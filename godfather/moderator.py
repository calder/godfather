import click
import datetime
import json
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
    self.last_fetch  = datetime.datetime.now()

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

  def send_email(self, to, subject, contents):
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

    if result.status_code == 200:
      logging.info("Email sent.")
    else:
      raise click.ClickException("Failed to send email (status code: %d): %s" %
                                 (result.status_code, result.text))

  def get_emails(self):
    """Return a list of emails received since the last check."""
    cutoff = datetime.datetime.now() - datetime.timedelta(minutes=1)

    # Fetch message list.
    response = requests.get(
      "https://api.mailgun.net/v3/caldercoalson.com/events",
      auth=("api", self.mailgun_key),
      params={
        "event": "stored",
        "begin": self.last_fetch.timestamp(),
        "end":   cutoff.timestamp(),
      }
    )
    if response.status_code == 200:
      logging.debug("GET /events: %d (%s):" % (response.status_code, response.reason))
      events = response.json()
      logging.debug(json.dumps(events, indent="  "))
    else:
      raise click.ClickException(
        "%d error (%s) getting events from Mailgun: %s" %
        (response.status_code, response.reason, response.text))

    message_urls = [event["storage"]["url"] for event in events["items"]
                    if "godfather@caldercoalson.com" in event["message"]["recipients"]]

    # Fetch message contents.
    messages = []
    for url in message_urls:
      response = requests.get(url, auth=("api", self.mailgun_key))
      if response.status_code == 200:
        logging.debug("GET /message: %d (%s):" % (response.status_code, response.reason))
        message = response.json()
        logging.debug(json.dumps(message, indent="  "))
      else:
        raise click.ClickException(
          "%d error (%s) getting message from Mailgun: %s" %
          (response.status_code, response.reason, response.text))

      sender = message["from"]
      body   = message["stripped-text"]
      messages.append((sender, body))

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
