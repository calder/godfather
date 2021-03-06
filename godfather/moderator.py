import click
import copy
import datetime
import json
import logging
import mafia
import os
import pickle
import requests
import termcolor
import signal
import sys
import time
import uuid

from godfather.api.message import Message
from godfather.messages import *

cancelled = False

def set_cancelled(c):
  global cancelled
  cancelled = c

def signal_handler(signal, frame):
  logging.info("Shutting down...")
  set_cancelled(True)

signal.signal(signal.SIGINT, signal_handler)

class Moderator(object):
  def __init__(self, *,
               path,
               game,
               game_name,
               time_zone,
               night_end,
               day_end,
               forum):
    assert day_end.tzinfo == time_zone
    assert night_end.tzinfo == time_zone

    self.path        = path
    self.game        = game
    self.name        = game_name

    self.time_zone   = time_zone
    self.night_end   = night_end
    self.day_end     = day_end

    self.started     = False
    self.phase       = mafia.Night(0)
    self.phase_end   = self.get_phase_end(start=self.get_time())
    self.forum       = forum
    self.parser      = mafia.Parser(self.game)

    self.game.log.on_append(self.event_logged)

  def get_phase_end(self, start):
    """Return the end of the current phase that started at <start>."""
    if   isinstance(self.phase, mafia.Night):
      return self.get_next_occurrence(start, self.night_end)
    elif isinstance(self.phase, mafia.Day):
      return self.get_next_occurrence(start, self.day_end)
    else:
      raise click.ClickException("Unknown phase: %s", type(self.phase))

  def get_next_occurrence(self, start, time):
    """Return the next occurence of time <time> after datetime <start>."""
    d = datetime.datetime.combine(start, time)
    if d < start:
      d += datetime.timedelta(days=1)
    return d.astimezone(self.time_zone)

  def get_time(self):
    """Return the current time."""
    return datetime.datetime.now(self.time_zone)

  def run(self):
    """Run the game until it finishes or an interrupt is received."""
    logging.info("Running %s..." % self.name)

    if not self.started:
      self.start()
      self.save()

    while True:
      for message in self.forum.get_messages(self.game, self.phase_end):
        self.message_received(message)

      if self.get_time() > self.phase_end + self.forum.receipt_lag:
        self.advance_phase()

      self.save()

      if self.game.is_game_over():
        self.end()
        return

      if not self.sleep():
        return

  def save(self):
    """Save the current Moderator state to disk."""
    pickle.dump(self, open(self.path, "wb"))

  def save_checkpoint(self, name):
    """Save the current Moderator state to a checkpoint file."""
    timestamp = datetime.datetime.now(self.time_zone).strftime("%Y-%m-%d_%H:%M:%S")
    backup_dir = os.path.join(os.path.dirname(self.path), "backups")
    checkpoint_path = os.path.join(backup_dir, "%s_%s.pickle" % (timestamp, name))
    pickle.dump(self, open(checkpoint_path, "wb"))

  def sleep(self):
    """Pause for a few seconds, and return whether execution should continue."""
    for i in range(10):
      if cancelled: return False
      time.sleep(1)
    return True

  def start(self):
    """Start the game and send out role messages."""
    self.save_checkpoint("setup")

    logging.info("Starting game...")
    body = render_message(
             "welcome.html",
             game_name=self.name,
             night_end=self.night_end.strftime("%I:%M %p"),
             day_end=self.day_end.strftime("%I:%M %p"),
             players=self.game.players,
           )
    self.send_message(mafia.events.PUBLIC, "%s: Start" % self.name, body)
    self.game.begin()
    self.started = True

    self.save_checkpoint("start")

  def end(self):
    """End the game and send out congratulation messages."""
    winners = mafia.str_player_list(self.game.winners())
    logging.info("Game over! Winners: %s" % winners)

    subject = "%s: The End" % self.name
    body = "Game over!\n\nCongratulations to %s for a well " \
           "(or poorly; I can't tell) played game!" % winners
    self.send_message(mafia.events.PUBLIC, subject, body)

  def advance_phase(self):
    """Resolve the current phase and start the next one."""
    self.game.resolve(self.phase)
    last_phase = self.phase
    self.phase = self.phase.next_phase()
    self.phase_end = self.get_phase_end(start=self.get_time())

    if not self.game.is_game_over():
      body = render_message(
               "end_of_phase.html",
               last_phase=last_phase,
               next_phase=self.phase,
               phase_end=self.phase_end.time().strftime("%I:%M %p"),
               players=self.game.players,
             )
      self.send_message(mafia.events.PUBLIC, self.current_subject, body)

    self.save_checkpoint(str(self.phase).lower().replace(' ', '_'))

  def send_message(self, to, subject, body):
    """Send a message to a player, list of players, or everyone."""
    self.forum.send_message(self.game, Message(to=to, subject=subject, body=body))

  def event_logged(self, event):
    """Called when an event is added to the game log."""
    prefix = termcolor.colored(">>>", "yellow")
    logging.info("%s %s" % (prefix, event.colored_str()))
    if event.to:
      subject = "%s: %s" % (self.name, event.phase)
      self.send_message(event.to, subject, event_email(event, parser=self.parser))

  def message_received(self, email):
    """Called when an email is received from a player."""
    prefix = termcolor.colored("◀◀◀", "yellow")
    logging.info("%s %s" % (prefix, email))

    try:
      if isinstance(self.phase, mafia.Day):
        old_votes = copy.copy(self.phase.votes)

      self.parser.parse(self.phase, email.sender, email.body)
      body = "Confirmed.\n\n> %s" % email.body
      self.send_message(email.sender, email.subject, body)

      if isinstance(self.phase, mafia.Day) and self.phase.votes != old_votes:
        voters = sorted([p for p in self.phase.votes.keys() if p and p.alive])
        votes = "\n".join(["  %s votes for %s." % (p, self.phase.votes[p]) for p in voters])
        body = "Current votes:\n%s" % votes
        self.send_message(mafia.events.PUBLIC, self.current_subject, body)

    except mafia.InvalidAction as e:
      body = "%s\n\n> %s" % (str(e), email.body)
      self.send_message(email.sender, email.subject, body)

    except mafia.HelpRequested:
      roles = self.game.log.to(email.sender).type(mafia.events.RoleAnnouncement)
      if len(roles) == 0:
        logging.warning("Could not find role announcement for player: %s" % email.sender)
      else:
        body = event_email(roles[-1], parser=self.parser)
        self.send_message(email.sender, email.subject, body)

  @property
  def current_subject(self):
    """Return the subject to use for phase-related announcements."""
    return "%s: %s" % (self.name, self.phase)
