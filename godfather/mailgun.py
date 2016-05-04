import click
import json
import logging
import requests

class Email(object):
  def __init__(self, *, sender=None, recipients=None, subject=None, body=None):
    self.sender     = sender
    self.recipients = recipients
    self.subject    = subject
    self.body       = body

  def __repr__(self):
    items = ["%r=%r" % (k, v) for k, v in self.__dict__.items() if v]
    return "Email(%s)" % ", ".join(items)

class Mailgun(object):
  def __init__(self, *, api_key, address, domain):
    self.api_key = api_key
    self.address = address
    self.domain  = domain

  def send_email(self, email):
    """Send an email or raise an exception if unable."""

    logging.info("Sending email:")
    logging.info("  To:      %s" % ", ".join(email.recipients))
    logging.info("  Subject: %s" % email.subject)
    logging.info("  Body:    %s" % email.body)

    result = requests.post(
        "https://api.mailgun.net/v3/%s/messages" % self.domain,
        auth=("api", self.mailgun_key),
        data={
          "from":    "The Godfather <%s@%s>" % (self.address, self.domain),
          "to":      to_emails,
          "subject": subject,
          "text":    contents,
        })

    if result.status_code != 200:
      raise click.ClickException("Failed to send email (status code: %d): %s" %
                                 (result.status_code, result.text))

    logging.info("Email sent.")

  def get_emails(self, start, end):
    """Return all emails received during the specified period."""

    logging.debug("Retrieving emails from %s to %s." % (start, end))

    # Fetch message list.
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

    events = response.json()

    # Fetch message contents.
    messages = []
    for event in events["items"]:
      if "%s@%s" % (self.address, self.domain) not in event["message"]["recipients"]:
        logging.debug("Discarding message addressed to a different recipient.")
        continue

      logging.debug("Retrieving email")
      response = requests.get(event["storage"]["url"],
                              auth=("api", self.api_key))
      if response.status_code != 200:
        raise click.ClickException(
          "%d error (%s) getting message from Mailgun: %s" %
          (response.status_code, response.reason, response.text))

      message = response.json()
      sender  = message["sender"]
      body    = message["stripped-text"]
      messages.append(Email(sender=sender, body=body))

    return messages
