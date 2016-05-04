import datetime
import nose
import functools
import os
import time
import unittest
import uuid

from unittest.mock import call, MagicMock
from mafia import assert_equal
from ..mailgun import *

class MailgunTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    key_path = os.path.expanduser("~/.config/godfather/mailgun_key.txt")
    api_key  = open(key_path).read().strip()
    self.mailgun1 = Mailgun(api_key=api_key,
                            sender="Electric Boogaloo 1",
                            address=str(uuid.uuid4()),
                            domain="caldercoalson.com")
    self.mailgun2 = Mailgun(api_key=api_key,
                            sender="Electric Boogaloo 2",
                            address=str(uuid.uuid4()),
                            domain="caldercoalson.com")

  @nose.plugins.attrib.attr("test-mailgun")
  def test_send(self):
    start = datetime.datetime.now()
    self.mailgun1.send_email(Email(
      recipients=["%s@%s" % (self.mailgun2.address, self.mailgun2.domain)],
      subject="Test", body="ohai."))
    time.sleep(1)
    self.mailgun1.send_email(Email(
      recipients=["%s@%s" % (self.mailgun2.address, self.mailgun2.domain)],
      subject="Test", body="kthxbai."))
    end = datetime.datetime.now() + datetime.timedelta(minutes=1)

    while datetime.datetime.now() < end:
      emails = self.mailgun2.get_emails(start, end)
      if len(emails) >= 2: break
      time.sleep(2)

    assert_equal(emails, [
      Email(sender=self.mailgun1.email, body="ohai."),
      Email(sender=self.mailgun1.email, body="kthxbai."),
    ])
