import click
import datetime
import json
import logging
import re
import requests
import requests.packages.urllib3

import mafia

from godfather.api.forum import Forum
from godfather.api.message import Message

# Disable "Starting new HTTPS connection" message.
requests.packages.urllib3.connectionpool.log.setLevel(logging.WARNING)


class Mailgun(Forum):
  def __init__(self, *, api_key, sender, address, domain, private_cc=None, public_cc=None):
    self.api_key    = api_key
    self.sender     = sender
    self.address    = address
    self.domain     = domain
    self.private_cc = private_cc or []
    self.public_cc  = public_cc or []
    self.last_fetch = datetime.datetime.now()

  @property
  def email(self):
    return "%s@%s" % (self.address, self.domain)

  @property
  def receipt_lag(self):
    # Mailgun does not guarantee that received messages will be immediately
    # visible via their API. If we check at 12:00:30, we should only assume
    # that messages up to 12:00:00 are already available.
    return datetime.timedelta(seconds=30)


  def strip_html(self, body):
    body = re.sub(r"\n +", "\n", body)
    body = re.sub(r"&lt;", "<", body)
    body = re.sub(r"&gt;", ">", body)
    body = re.sub(r"</h2>", ":", body)
    body = re.sub(r"<li>", "  - ", body)
    body = re.sub(r"\n</?ul>\n", "\n", body)
    body = re.sub(r"<\w+?>|</\w+?>", "", body)
    return body

  def send_message(self, game, message):
    """Send a message or raise an exception if unable."""

    to = message.to
    cc = self.private_cc
    if to == mafia.events.PUBLIC:
      to = game.all_players
      cc = cc + self.public_cc
    if not isinstance(to, list):
      to = [to]

    to = ["%s <%s>" % (p.name, p.info["email"]) for p in to]

    logging.info("Sending email:")
    logging.info("  To:      %s" % ", ".join(to))
    logging.info("  Subject: %s" % message.subject)
    logging.info("  Body:\n%s" % self.strip_html(message.body))

    result = requests.post(
        "https://api.mailgun.net/v3/%s/messages" % self.domain,
        auth=("api", self.api_key),
        data={
          "from":    "%s <%s>" % (self.sender, self.email),
          "to":      to,
          "cc":      cc,
          "subject": message.subject,
          "text":    self.strip_html(message.body),
          "html":    message.body,
        })

    if result.status_code != 200:
      raise click.ClickException("Failed to send email (status code: %d): %s" %
                                 (result.status_code, result.text))

    logging.info("Message sent.")

  def get_messages(self, game, cutoff):
    """Return a list of messages received since the last check."""
    cutoff = min(cutoff, datetime.datetime.now(cutoff.tzinfo) - self.receipt_lag)
    messages = self._get_messages_from(game, self.last_fetch, cutoff)
    self.last_fetch = cutoff
    return messages

  def _get_messages_from(self, game, start, end):
    """Return all messages received during the specified period."""
    logging.debug("Retrieving emails from %s to %s." % (start, end))

    # Fetch message list
    response = requests.get(
      "https://api.mailgun.net/v3/%s/events" % self.domain,
      auth=("api", self.api_key),
      params={
        "event": "stored",
        "begin": start.timestamp(),
        "end":   end.timestamp(),
      }
    )
    if response.status_code != 200:
      raise click.ClickException(
        "%d error (%s) getting events from Mailgun: %s" %
        (response.status_code, response.reason, response.text))

    # Parse messages
    messages = []
    events = response.json()
    players = {p.info["email"]: p for p in game.all_players}
    for event in events["items"]:
      if self.email not in event["message"]["recipients"]:
        logging.debug("Discarding message addressed to '%s'." % event["message"]["recipients"])
        continue

      logging.debug("Retrieving email")
      response = requests.get(event["storage"]["url"],
                              auth=("api", self.api_key))
      if response.status_code != 200:
        raise click.ClickException(
          "%d error (%s) getting message from Mailgun: %s" %
          (response.status_code, response.reason, response.text))

      email = response.json()
      sender  = email["sender"]
      subject = email["subject"]
      body    = email["stripped-text"]

      if sender in players:
        logging.info("Received message from '%s'." % sender)
        messages.append(Message(sender=players[sender], subject=subject, body=body))
      else:
        logging.warning("Discarding message from non-player '%s'." % sender)
        send_message(Message(
          recipients=[sender],
          subject=subject,
          body="Unrecognized player: '%s'." % sender))

    return messages
