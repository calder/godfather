import datetime
import nose
import functools
import os
import pytz
import time
import unittest
import uuid

from nose.plugins.attrib import attr
from mafia import assert_equal
from unittest.mock import call, MagicMock

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
    self.mailgun3 = Mailgun(api_key=api_key,
                            sender="Electric Boogaloo 3",
                            address=str(uuid.uuid4()),
                            domain="caldercoalson.com")

  @attr("test-mailgun")
  def test_send(self):
    start = datetime.datetime.now(pytz.UTC)
    self.mailgun1.send_email(Email(
      recipients=["%s@%s" % (self.mailgun2.address, self.mailgun2.domain)],
      cc=["%s@%s" % (self.mailgun3.address, self.mailgun3.domain)],
      subject="Test", body="ohai."))
    time.sleep(1)
    self.mailgun1.send_email(Email(
      recipients=["%s@%s" % (self.mailgun2.address, self.mailgun2.domain)],
      cc=["%s@%s" % (self.mailgun3.address, self.mailgun3.domain)],
      subject="Test", body="kthxbai."))
    end = datetime.datetime.now(pytz.UTC) + datetime.timedelta(minutes=1)

    while datetime.datetime.now(pytz.UTC) < end:
      emails2 = self.mailgun2.get_emails(start, end)
      emails3 = self.mailgun2.get_emails(start, end)
      if len(emails2) >= 2 and len(emails3) >= 2: break
      time.sleep(2)

    assert_equal(emails2, [
      Email(sender=self.mailgun1.email, subject="Test", body="ohai."),
      Email(sender=self.mailgun1.email, subject="Test", body="kthxbai."),
    ])
    assert_equal(emails3, [
      Email(sender=self.mailgun1.email, subject="Test", body="ohai."),
      Email(sender=self.mailgun1.email, subject="Test", body="kthxbai."),
    ])
