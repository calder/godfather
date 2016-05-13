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
    self.phase_end   = self.get_phase_end(start=self.get_time())
    self.last_fetch  = self.get_time()
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
    d = start.replace(hour=time.hour, minute=time.minute, second=time.second)
    if d < start:
      d = d + datetime.timedelta(days=1)
    return d

  def get_time(self):
    """Return the current time. Overridden in tests."""
    return datetime.datetime.now()

  def run(self):
    """Run the game until it finishes or an interrupt is received."""
    logging.info("Running %s..." % self.name)

    if not self.started:
      self.start()
      self.save()

    while True:
      for email in self.get_emails():
        self.email_received(email)

      if self.get_time() > self.phase_end:
        self.advance_phase()

      self.save()

      if self.game.is_game_over():
        self.end()
        return

      if not self.sleep():
        return

  def save(self):
    """Save the current Moderator state to disk. Overridden in tests."""
    pickle.dump(self, open(self.path, "wb"))

  def sleep(self):
    """Pause for a few seconds, and return whether execution should continue.
    Overridden in tests."""
    time.sleep(10)
    return True  # TODO: Check for interrupts

  def start(self):
    """Start the game and send out role emails."""
    logging.info("Starting game...")
    players = "\n".join([p.name for p in self.game.all_players])
    welcome = "Welcome to %s. You will receive your roles via email shortly." \
              "You may discuss them all you like, but under no circumstances " \
              "may you show another player any email you receive from me.\n\n" \
              "Night 0 begins tonight.\n" \
              "Night actions are due by %s.\n" \
              "Day actions are due by %s.\n\n" \
              "Your fellow players:\n%s" % \
              (self.name, self.night_end, self.day_end, players)
    self.send_email(mafia.events.PUBLIC, "%s: Welcome" % self.name, welcome)
    self.game.begin()
    self.started = True

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
    self.phase = self.phase.next_phase()
    self.phase_end = self.get_phase_end(start=self.get_time())

    if not self.game.is_game_over():
      phase_end = self.phase_end.time().strftime("%I:%M %p")
      subject = "%s: %s" % (self.name, self.phase)
      body = "%s actions are due by %s." % (self.phase, phase_end)
      self.send_email(mafia.events.PUBLIC, subject, body)

  def send_email(self, to, subject, body):
    """Send an email to a list of players, or everyone if to=PUBLIC.
    Overridden in tests."""
    assert to
    if to == mafia.events.PUBLIC:
      to = self.game.all_players
    recipients = ["%s <%s>" % (p.name, p.info["email"]) for p in to]

    self.mailgun.send_email(Email(recipients=recipients, subject=subject, body=body))

  def get_emails(self):
    """Return a list of emails received since the last check.
    Overridden in tests."""
    cutoff = self.get_time() - datetime.timedelta(minutes=1)
    cutoff = min(cutoff, self.phase_end)

    messages = []
    for email in self.mailgun.get_emails(self.last_fetch, cutoff):
      if email.sender in self.players:
        messages.append(Email(sender=self.players[email.sender],
                              subject=email.subject,
                              body=email.body))
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
      self.send_email(to, subject, event.full_message)

  def email_received(self, message):
    """Called when an email is received from a player."""
    action = message.body.strip().split("\n")[0].strip(".!?> \t").lower()
    prefix = termcolor.colored("◀◀◀", "yellow")
    logging.info("%s %s" % (prefix, message))

    try:
      self.phase.add_parsed(message.sender, action, game=self.game)
    except mafia.InvalidAction as e:
      body = "%s\n\n> %s" % (str(e), action)
      self.send_email(message.sender, message.subject, body)
