import click
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

from .mailgun import *

# Mailgun does not guarantee that received messages will be immediately
# visible via their API. If we check at 12:00:30, we should only assume
# that messages up to 12:00:00 are already available.
MAIL_DELIVERY_LAG = datetime.timedelta(seconds=30)

cancelled = False

def set_cancelled(c):
  global cancelled
  cancelled = c

def signal_handler(signal, frame):
  logging.info("Shutting down...")
  set_cancelled(True)

signal.signal(signal.SIGINT, signal_handler)

class Moderator(object):
  def __init__(self, *, path, game,
               game_name, moderator_name,
               public_cc=None, private_cc=None,
               time_zone, night_end, day_end,
               domain, mailgun_key):
    assert day_end.tzinfo == time_zone
    assert night_end.tzinfo == time_zone

    self.path        = path
    self.game        = game
    self.name        = game_name

    self.public_cc   = public_cc or []
    self.private_cc  = private_cc or []

    self.time_zone   = time_zone
    self.night_end   = night_end
    self.day_end     = day_end

    self.started     = False
    self.players     = {p.info["email"]: p for p in game.all_players}
    self.phase       = mafia.Night(0)
    self.phase_end   = self.get_phase_end(start=self.get_time())
    self.last_fetch  = self.get_time()
    self.mailgun     = Mailgun(api_key=mailgun_key,
                               sender=moderator_name,
                               address=str(uuid.uuid4()),
                               domain=domain)
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
      for email in self.get_emails():
        self.email_received(email)

      if self.get_time() > self.phase_end + MAIL_DELIVERY_LAG:
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
    timestamp = datetime.datetime.now(self.time_zone).strftime("%Y-%m-%d %H:%M:%S")
    backup_dir = os.path.join(os.path.dirname(self.path), "backups")
    checkpoint_path = os.path.join(backup_dir, "game %s %s.pickle" % (timestamp, name))
    pickle.dump(self, open(checkpoint_path, "wb"))

  def sleep(self):
    """Pause for a few seconds, and return whether execution should continue."""
    for i in range(10):
      if cancelled: return False
      time.sleep(1)
    return True

  def start(self):
    """Start the game and send out role emails."""
    self.save_checkpoint("Setup")

    logging.info("Starting game...")
    players = "\n".join(["  %s <%s>" % (p.name, p.info["email"]) for p in self.game.all_players])
    welcome = "Welcome to %s. You will receive your roles via email shortly." \
              "You may discuss them all you like, but under no circumstances " \
              "may you show another player any email you receive from me.\n\n" \
              "Night actions are due by %s.\n" \
              "Day actions are due by %s.\n\n" \
              "Night 0 begins tonight.\n\n" \
              "Your fellow players:\n%s" % (
                self.name,
                self.night_end.strftime("%I:%M %p"),
                self.day_end.strftime("%I:%M %p"),
                players
              )
    self.send_email(mafia.events.PUBLIC, "%s: Welcome" % self.name, welcome)
    self.game.begin()
    self.started = True

    self.save_checkpoint("Start")

  def end(self):
    """End the game and send out congratulation emails."""
    winners = mafia.str_player_list(self.game.winners())
    logging.info("Game over! Winners: %s" % winners)

    subject = "%s: The End" % self.name
    body = "Game over!\n\nCongratulations to %s for a well " \
           "(or poorly; I can't tell) played game!" % winners
    self.send_email(mafia.events.PUBLIC, subject, body)

  def advance_phase(self):
    """Resolve the current phase and start the next one."""
    self.game.resolve(self.phase)
    last_phase = self.phase
    self.phase = self.phase.next_phase()
    self.phase_end = self.get_phase_end(start=self.get_time())

    if not self.game.is_game_over():
      phase_end = self.phase_end.time().strftime("%I:%M %p")
      players = "\n".join(["  " + p.name for p in self.game.players])
      body = "%s is over. %s actions are due by %s.\n\n"\
             "Remaining players:\n%s" % \
             (last_phase, self.phase, phase_end, players)
      self.send_email(mafia.events.PUBLIC, self.current_subject, body)

    self.save_checkpoint(str(self.phase))

  def send_email(self, to, subject, body):
    """Send an email to a player, list of players, or everyone."""
    cc = self.private_cc
    assert to
    if to == mafia.events.PUBLIC:
      to = self.game.all_players
      cc = cc + self.public_cc
    if not isinstance(to, list):
      to = [to]
    recipients = ["%s <%s>" % (p.name, p.info["email"]) for p in to]

    self.mailgun.send_email(Email(recipients=recipients, cc=cc, subject=subject, body=body))

  def get_emails(self):
    """Return a list of emails received since the last check."""
    cutoff = self.get_time() - MAIL_DELIVERY_LAG
    cutoff = min(cutoff, self.phase_end)

    messages = []
    for email in self.mailgun.get_emails(self.last_fetch, cutoff):
      sender = email.sender.lower()
      if sender in self.players:
        messages.append(Email(sender=self.players[sender],
                              subject=email.subject,
                              body=email.body))
      else:
        logging.info("Discarding message from non-player '%s'." % sender)
        self.mailgun.send_email(Email(
          recipients=[email.sender],
          subject=email.subject,
          body="Unrecognized player: '%s'." % sender))

    self.last_fetch = cutoff
    return messages

  def event_logged(self, event):
    """Called when an event is added to the game log."""
    prefix = termcolor.colored(">>>", "yellow")
    logging.info("%s %s" % (prefix, event.colored_str()))
    if event.to:
      subject = "%s: %s" % (self.name, event.phase)
      self.send_email(event.to, subject, event.full_message)

  def email_received(self, email):
    """Called when an email is received from a player."""
    action = email.body.strip().split("\n")[0].strip().strip(".!?>").lower()
    prefix = termcolor.colored("◀◀◀", "yellow")
    logging.info("%s %s" % (prefix, email))

    try:
      self.parser.parse(self.phase, email.sender, action)
      if isinstance(self.phase, mafia.Day):
        voters = sorted([p for p in self.phase.votes.keys() if p and p.alive])
        votes = "\n".join(["  %s votes for %s." % (p, self.phase.votes[p]) for p in voters])
        body = "Current votes:\n%s" % votes
        self.send_email(mafia.events.PUBLIC, self.current_subject, body)
      else:
        body = "Confirmed: %s" % action
        self.send_email(email.sender, email.subject, body)
    except mafia.InvalidAction as e:
      body = "%s\n\n> %s" % (str(e), action)
      self.send_email(email.sender, email.subject, body)

  @property
  def current_subject(self):
    """Return the subject to use for phase-related announcements."""
    return "%s: %s" % (self.name, self.phase)
