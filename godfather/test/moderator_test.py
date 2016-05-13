import datetime
import os
import pickle
import pluginbase
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
    self.masons  = self.game.add_faction(Masonry("Fellowship", self.town))
    self.mafia   = self.game.add_faction(Mafia("Forces of Darkness"))
    self.frodo   = self.game.add_player("Frodo", Villager(self.masons),
                                        info={"email": "frodo@shire.gov"})
    self.sam     = self.game.add_player("Samwise", Villager(self.masons),
                                        info={"email": "sam@samsgardening.com"})
    self.gandalf = self.game.add_player("Gandalf", Cop(self.town),
                                        info={"email": "mithrandir@meu.edu"})
    self.sauron  = self.game.add_player("Sauron", Godfather(self.mafia),
                                        info={"email": "sauron@mordor.gov"})
    self.moderator = Moderator(path=self.game_path,
                               game=self.game,
                               name="LOTR Mafia",
                               night_end=datetime.time(hour=10),
                               day_end=datetime.time(hour=22),
                               mailgun_key="Fake Key")
    self.moderator.get_time = self.mocks.get_time = MagicMock()
    self.moderator.mailgun  = self.mocks.mailgun  = MagicMock()
    self.moderator.sleep    = self.mocks.sleep    = MagicMock()

    self.moderator.get_time.return_value = datetime.datetime.now()

class ModeratorUnitTest(ModeratorTest):
  def setUp(self):
    super().setUp()
    self.emails = []
    self.moderator.save       = self.mocks.save       = MagicMock()
    self.moderator.send_email = self.mocks.send_email = MagicMock()
    self.moderator.get_emails = self.mocks.get_emails = MagicMock()
    self.moderator.get_emails.side_effect = self.get_and_clear_emails

  def get_and_clear_emails(self):
    emails = self.emails
    self.emails = []
    return emails

  def assert_sent_emails(self, calls):
    assert_equal(self.moderator.send_email.mock_calls, calls)
    self.moderator.send_email.reset_mock()

  def test_simple_game(self):
    def logic():
      # Pass 1: Role and faction emails should be sent.
      subject = "LOTR Mafia: Start"
      self.assert_sent_emails([
        call(events.PUBLIC, "LOTR Mafia: Welcome", StartsWith("Welcome to LOTR Mafia.")),
        call([self.frodo],   subject, StartsWith("You are the Mason Villager.")),
        call([self.gandalf], subject, StartsWith("You are the Town Cop.")),
        call([self.sam],     subject, StartsWith("You are the Mason Villager.")),
        call([self.sauron],  subject, StartsWith("You are the Mafia Godfather.")),
        call([self.frodo, self.sam], subject, "Frodo and Samwise, you are the Fellowship."),
        call([self.sauron],  subject, StartsWith("You are the leader of the Forces of Darkness."))
      ])
      assert self.moderator.started

      # Pass 2: Send in some action emails.
      self.emails.append(Email(sender=self.sam, subject="Mafia", body="Protect Frodo!"))
      self.emails.append(Email(sender=self.sauron, subject="Mafia", body="Sauron: Kill Frodo."))
      yield True
      self.assert_sent_emails([
        call(self.sam, "Mafia", "No actions available.\n\n> protect frodo"),
      ])

      # Pass 3: Advance the clock so night resolves.
      self.moderator.get_time.return_value = self.moderator.phase_end + \
                                             datetime.timedelta(seconds=1)
      yield True
      self.assert_sent_emails([
        call(events.PUBLIC, "LOTR Mafia: Night 0", "Frodo, the Mason Villager, has died."),
        call(events.PUBLIC, "LOTR Mafia: Night 0", "Night 0 is over. Day 1 actions are due by 10:00 PM."),
      ])

      # Pass 4: Send in some vote emails.
      self.emails.append(Email(sender=self.sam, subject="My Vote", body="vote sauron"))
      self.emails.append(Email(sender=self.sauron, subject="Mafia", body="GRRRRRRRRR"))
      yield True
      self.assert_sent_emails([
        call(self.sauron, "Mafia", StartsWith("Votes must take the form:")),
      ])

      # Pass 5: Advance the clock so day resolves.
      self.moderator.get_time.return_value = self.moderator.phase_end + \
                                             datetime.timedelta(seconds=1)
      yield True
      self.assert_sent_emails([
        call(events.PUBLIC, "LOTR Mafia: Day 1", "Sauron, the Mafia Godfather, was lynched."),
        call(events.PUBLIC, "LOTR Mafia: The End", Glob("*Congratulations to Frodo, Gandalf and Samwise*")),
      ])

      # Exit
      yield "Foobar"

    test_logic = logic()
    self.moderator.sleep.side_effect = test_logic
    self.moderator.run()
    assert_equal(next(test_logic), "Foobar")

  def test_get_next_occurrence(self):
    now  = datetime.datetime(year=2001, month=1, day=1, hour=11, second=30)
    time = datetime.time(hour=12)
    next = datetime.datetime(year=2001, month=1, day=1, hour=12)
    assert_equal(next, self.moderator.get_next_occurrence(now, time))

    now  = datetime.datetime(year=2001, month=1, day=1, hour=13, second=30)
    time = datetime.time(hour=12)
    next = datetime.datetime(year=2001, month=1, day=2, hour=12)
    assert_equal(next, self.moderator.get_next_occurrence(now, time))

class ModeratorFunctionalTest(ModeratorTest):

  def address(self, player):
    return "%s <%s>" % (player.name, player.info["email"])

  def test_send_public_email(self):
    self.moderator.send_email(events.PUBLIC, "Test", "Test body.")
    assert_equal(self.moderator.mailgun.mock_calls, [
      call.send_email(Email(
        recipients=[self.address(p) for p in self.game.players],
        subject="Test",
        body="Test body.")
      )
    ])

  def test_send_private_email(self):
    self.moderator.send_email(self.sam, "Test", "Test body.")
    assert_equal(self.moderator.mailgun.mock_calls, [
      call.send_email(Email(
        recipients=[self.address(self.sam)],
        subject="Test",
        body="Test body.")
      )
    ])

  def test_send_group_email(self):
    self.moderator.send_email([self.sam, self.frodo], "Test", "Test body.")
    assert_equal(self.moderator.mailgun.mock_calls, [
      call.send_email(Email(
        recipients=[self.address(self.sam), self.address(self.frodo)],
        subject="Test",
        body="Test body.")
      )
    ])

  def test_get_emails(self):
    pass
