import click
import datetime
import json
import logging
import mafia
import pickle
import requests
import termcolor
import time
import uuid

from .mailgun import *

class Moderator(object):
  def __init__(self, *, path, game, name, night_end, day_end, mailgun_key):
    self.path        = path
    self.game        = game
    self.name        = name
    self.night_end   = night_end
    self.day_end     = day_end

    self.started     = False
    self.players     = {p.info["email"]: p for p in game.all_players}
    self.phase       = mafia.Night(0)
    self.phase_end   = self.get_phase_end(start=datetime.datetime.now())
    self.last_fetch  = datetime.datetime.now()
    self.mailgun     = Mailgun(api_key=mailgun_key,
                               sender="The Godfather",
                               address=str(uuid.uuid4()),
                               domain="caldercoalson.com")

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
    d = start.replace(hour=time.hour, minute=time.minute)
    if d < start:
      d = d + datetime.timedelta(days=1)
    return d

  def run(self, *, setup_only=False):
    """Run the game until it finishes or an interrupt is received."""
    logging.info("Running %s..." % self.name)

    if not self.started:
      self.start()
      self.save()

    if setup_only:
      return

    while True:
      for email in self.get_emails():
        self.email_received(email)

      if datetime.datetime.now() > self.phase_end:
        self.advance_phase()

      self.save()

      if self.game.is_game_over():
        logging.info("Game over!")
        return

      time.sleep(60)

  def save(self):
    """Save the current Moderator state to disk."""
    pickle.dump(self, open(self.path, "wb"))

  def start(self):
    """Start the game and send out role emails."""
    logging.info("Starting game...")
    self.game.begin()
    self.started = True

  def advance_phase(self):
    """Resolve the current phase and start the next one."""
    pass # Placeholder

  def send_email(self, to, subject, contents):
    """Send an email to a list of players, or everyone if to=PUBLIC."""
    assert to
    if to == mafia.events.PUBLIC:
      to = self.game.all_players
    recipients = ["%s <%s>" % (p.name, p.info["email"]) for p in to]

    self.mailgun.send_email(Email(recipients=recipients, subject=subject, body=body))

  def get_emails(self):
    """Return a list of emails received since the last check."""
    cutoff = datetime.datetime.now() - datetime.timedelta(minutes=1)

    messages = []
    for email in self.mailgun.get_emails(self.last_fetch, cutoff):
      if email.sender in self.players:
        messages.append(Email(sender=self.players[email.sender], body=email.body))
      else:
        logging.info("Discarding message from non-player '%s'." % email.sender)

    self.last_fetch = cutoff
    return messages

  def event_logged(self, event):
    """Called when an event is added to the game log."""
    prefix = termcolor.colored(">>>", "yellow")
    logging.info("%s %s" % (prefix, event.colored_str()))
    if event.to:
      to = event.to
      subject = "%s: %s" % (self.name, event.phase)
      self.send_email(to, subject, event.message)

  def email_received(self, message):
    """Called when an email is received from a player."""
    prefix = termcolor.colored("▶▶▶", "yellow")
    logging.info("%s %s" % (prefix, message))
    # Placeholder
