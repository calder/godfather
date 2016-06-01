import datetime
import os
import pickle
import pluginbase
import pytz
import unittest

from callee import Glob, StartsWith
from .cli_test import *
from mafia import *
from unittest.mock import ANY, call, MagicMock

from ..moderator import *

class ModeratorTest(CliTest):
  def setUp(self):
    super().setUp()
    self.mocks   = MagicMock()
    self.game    = Game()
    self.town    = self.game.add_faction(Town())
    self.masons  = self.game.add_faction(Masonry("The Fellowship", self.town))
    self.mafia   = self.game.add_faction(Mafia("The Forces of Darkness"))
    self.frodo   = self.game.add_player("Frodo", Villager(self.masons),
                                        info={"email": "frodo@bagend.shire"})
    self.sam     = self.game.add_player("Samwise", Villager(self.masons),
                                        info={"email": "sam@samsgardening.com"})
    self.gandalf = self.game.add_player("Gandalf", Cop(self.town),
                                        info={"email": "mithrandir@meu.edu"})
    self.sauron  = self.game.add_player("Sauron", Godfather(self.mafia),
                                        info={"email": "sauron@mordor.gov"})
    time_zone = pytz.timezone("US/Pacific-New")
    self.moderator = Moderator(path=self.game_path,
                               game=self.game,
                               game_name="LOTR Mafia",
                               moderator_name="The Ghost of J.R.R. Tolkien",
                               domain="exeter.ox.ac.uk",
                               time_zone=time_zone,
                               night_end=datetime.time(hour=10, tzinfo=time_zone),
                               day_end=datetime.time(hour=22, tzinfo=time_zone),
                               mailgun_key="Fake Key")
    self.moderator.get_time = self.mocks.get_time = MagicMock()
    self.moderator.mailgun  = self.mocks.mailgun  = MagicMock()
    self.moderator.sleep    = self.mocks.sleep    = MagicMock()

    self.moderator.get_time.return_value = datetime.datetime.now(pytz.UTC)

class ModeratorUnitTest(ModeratorTest):
  """These tests mock out all of Moderator's "side effect" methods."""

  def setUp(self):
    super().setUp()
    self.emails = []
    self.moderator.save            = self.mocks.save            = MagicMock()
    self.moderator.save_checkpoint = self.mocks.save_checkpoint = MagicMock()
    self.moderator.send_email      = self.mocks.send_email      = MagicMock()
    self.moderator.get_emails      = self.mocks.get_emails      = MagicMock()
    self.moderator.get_emails.side_effect = self.get_and_clear_emails

  def get_and_clear_emails(self):
    emails = self.emails
    self.emails = []
    return emails

  def assert_sent_emails(self, calls):
    assert_equal(self.moderator.send_email.mock_calls, calls)
    self.moderator.send_email.reset_mock()

  def advance_phase(self):
    self.moderator.get_time.return_value = self.moderator.phase_end + \
                                           MAIL_DELIVERY_LAG + \
                                           datetime.timedelta(seconds=1)

  def test_simple_game(self):
    def logic():
      # Pass 1: Role and faction emails should be sent.
      subject = "LOTR Mafia: Start"
      self.assert_sent_emails([
        call(events.PUBLIC, "LOTR Mafia: Welcome", StartsWith("Welcome to <b>LOTR Mafia</b>.")),
        call([self.frodo],   subject, StartsWith("You are the <b>Mason Villager</b>.")),
        call([self.gandalf], subject, StartsWith("You are the <b>Town Cop</b>.")),
        call([self.sam],     subject, StartsWith("You are the <b>Mason Villager</b>.")),
        call([self.sauron],  subject, StartsWith("You are the <b>Mafia Godfather</b>.")),
        call([self.frodo, self.sam], subject, "You are The Fellowship."),
        call([self.sauron],  subject, StartsWith("You are the leader of The Forces of Darkness."))
      ])
      assert self.moderator.started

      # Pass 1.5: Sauron is confused.
      self.emails.append(Email(sender=self.sauron, subject="???", body="Help me!"))
      yield True
      self.assert_sent_emails([
        call(self.sauron, "???", Glob("*sauron: kill PLAYER*")),
      ])

      # Pass 2: Send in some action emails.
      self.emails.append(Email(sender=self.sam, subject="Mafia", body="Protect Frodo!"))
      self.emails.append(Email(sender=self.sauron, subject="Mafia", body="Sauron: Kill Frodo."))
      yield True
      self.assert_sent_emails([
        call(self.sam, "Mafia", "Invalid action.\n\n> Protect Frodo!"),
        call(self.sauron, "Mafia", "Confirmed.\n\n> Sauron: Kill Frodo."),
      ])

      # Pass 3: Advance the clock so night resolves.
      self.advance_phase()
      yield True
      self.assert_sent_emails([
        call(events.PUBLIC, "LOTR Mafia: Night 0", "Frodo, the <b>Mason Villager</b>, has died."),
        call(events.PUBLIC, "LOTR Mafia: Day 1", StartsWith("Night 0 is over. Day 1 actions are due by 10:00 PM.")),
      ])

      # Pass 4: Send in some vote emails.
      self.emails.append(Email(sender=self.sam, subject="My Vote", body="vote sauron\r\n-Sam"))
      self.emails.append(Email(sender=self.sauron, subject="Mafia", body="GRRRRRRRRR"))
      yield True
      self.assert_sent_emails([
        call(events.PUBLIC, "LOTR Mafia: Day 1", "Current votes:\n  Samwise votes for Sauron."),
        call(self.sauron, "Mafia", "Invalid action.\n\n> GRRRRRRRRR"),
      ])

      # Pass 5: Advance the clock so day resolves.
      self.advance_phase()
      yield True
      self.assert_sent_emails([
        call(events.PUBLIC, "LOTR Mafia: Day 1", "Sauron, the <b>Mafia Godfather</b>, was lynched."),
        call(events.PUBLIC, "LOTR Mafia: The End", Glob("*Congratulations to Frodo, Gandalf and Samwise*")),
      ])

      # Exit
      yield "Foobar"

    test_logic = logic()
    self.moderator.sleep.side_effect = test_logic
    self.moderator.run()
    assert_equal(next(test_logic), "Foobar")

  def test_get_next_occurrence(self):
    # Same day
    now  = datetime.datetime(year=2001, month=1, day=1, hour=11, second=30, tzinfo=pytz.UTC)
    time = datetime.time(hour=12, tzinfo=pytz.UTC)
    next = datetime.datetime(year=2001, month=1, day=1, hour=12, tzinfo=pytz.UTC)
    assert_equal(next, self.moderator.get_next_occurrence(now, time))

    # Next day
    now  = datetime.datetime(year=2001, month=1, day=1, hour=13, second=30, tzinfo=pytz.UTC)
    time = datetime.time(hour=12, tzinfo=pytz.UTC)
    next = datetime.datetime(year=2001, month=1, day=2, hour=12, tzinfo=pytz.UTC)
    assert_equal(next, self.moderator.get_next_occurrence(now, time))

    # Different timezones
    now  = datetime.datetime(year=2001, month=1, day=1, hour=13, second=30, tzinfo=pytz.UTC)
    time = datetime.time(hour=12, tzinfo=pytz.timezone("Etc/GMT+1"))
    next = datetime.datetime(year=2001, month=1, day=2, hour=12, tzinfo=pytz.timezone("Etc/GMT+1"))
    assert_equal(next, self.moderator.get_next_occurrence(now, time))

class ModeratorSaveTest(ModeratorTest):
  """Test save and save_checkpoint."""

class ModeratorEmailTest(ModeratorTest):
  """Test get_emails and send_emails with a mocked out Mailgun object."""

  def setUp(self):
    super().setUp()
    self.moderator.public_cc = ["public@gmail.com"]
    self.moderator.private_cc = ["private@gmail.com"]

  def address(self, player):
    return "%s <%s>" % (player.name, player.info["email"])

  def test_send_public_email(self):
    self.moderator.send_email(events.PUBLIC, "Test", "Test body.")
    assert_equal(self.moderator.mailgun.mock_calls, [
      call.send_email(Email(
        recipients=[self.address(p) for p in self.game.players],
        cc=["private@gmail.com", "public@gmail.com"],
        subject="Test",
        body="Test body.")
      )
    ])

  def test_send_private_email(self):
    self.moderator.send_email(self.sam, "Test", "Test body.")
    assert_equal(self.moderator.mailgun.mock_calls, [
      call.send_email(Email(
        recipients=[self.address(self.sam)],
        cc=["private@gmail.com"],
        subject="Test",
        body="Test body.")
      )
    ])

  def test_send_group_email(self):
    self.moderator.send_email([self.sam, self.frodo], "Test", "Test body.")
    assert_equal(self.moderator.mailgun.mock_calls, [
      call.send_email(Email(
        recipients=[self.address(self.sam), self.address(self.frodo)],
        cc=["private@gmail.com"],
        subject="Test",
        body="Test body.",
      ))
    ])

  def test_get_emails(self):
    now = datetime.datetime(year=2001, month=1, day=1, hour=1, tzinfo=pytz.UTC)
    self.moderator.last_fetch = now - datetime.timedelta(days=1)
    self.moderator.get_time.return_value = now
    emails = self.moderator.get_emails()
    assert_equal(emails, [])
    assert_equal(self.moderator.last_fetch, now - MAIL_DELIVERY_LAG)

    self.moderator.mailgun.get_emails.return_value = [
      Email(sender="frodo@bagend.shire",    subject="1", body="Body 1"),
      Email(sender="sam@samsgardening.com", subject="2", body="Body 2"),
      Email(sender="saruman@orthanc.me",    subject="3", body="Body 3"),
    ]
    emails = self.moderator.get_emails()
    assert_equal(emails, [
      Email(sender=self.frodo, subject="1", body="Body 1"),
      Email(sender=self.sam,   subject="2", body="Body 2"),
    ])
    self.moderator.mailgun.send_email.assert_called_with(Email(
      recipients=["saruman@orthanc.me"],
      subject="3",
      body="Unrecognized player: 'saruman@orthanc.me'.",
    ))
    assert_equal(self.moderator.last_fetch, now - MAIL_DELIVERY_LAG)
