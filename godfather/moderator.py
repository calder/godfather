import click
import datetime
import logging
import mafia
import pickle
import requests
import termcolor

class Moderator(object):
  def __init__(self, *, path, game, name, night_end, day_end, mailgun_key):
    self.path        = path
    self.game        = game
    self.name        = name
    self.night_end   = night_end
    self.day_end     = day_end
    self.mailgun_key = mailgun_key

    self.started     = False
    self.phase       = mafia.Night(0)
    self.phase_end   = self.get_phase_end(start=datetime.datetime.now())

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
    """Entry point. Blocks until game finishes or an interrupt is received."""
    logging.info("Moderating game...")
    if not self.started:
      self.start()
    if setup_only:
      return

  def start(self):
    """Start the game and send out role emails."""
    logging.info("Starting game...")
    self.game.begin()
    self.started = True
    self.save()

  def save(self):
    """Save the current Moderator state to disk."""
    pickle.dump(self, open(self.path, "wb"))

  def email(self, to, subject, contents):
    """Send an email to a list of players, or everyone if to=PUBLIC."""
    assert to
    if to == mafia.events.PUBLIC:
      to = self.game.all_players
    to_emails = ["%s <%s>" % (p.name, p.email) for p in to]
    to_str = ", ".join(to_emails)

    logging.info("Sending email:")
    logging.info("  To:       %s" % to_str)
    logging.info("  Subject:  %s" % subject)
    logging.info("  Contents: %s" % contents)

    result = requests.post(
        "https://api.mailgun.net/v3/caldercoalson.com/messages",
        auth=("api", self.mailgun_key),
        data={
          "from": "The Godfather <godfather@caldercoalson.com>",
          "to": to_emails,
          "subject": subject,
          "text": contents,
        })

    if result.status_code != 200:
      raise click.ClickException("Failed to send email (status code: %d): %s" %
                                 (result.status_code, result.text))

    logging.info("Email sent.")

  def event_logged(self, event):
    """Called when an event is added to the game log."""
    prefix = termcolor.colored(">>>", "yellow")
    logging.info("%s %s" % (prefix, event.colored_str()))
    if event.to:
      to = event.to
      subject = "%s: %s" % (self.name, event.phase)
      self.email(to, subject, event.message)
