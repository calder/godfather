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

class MockForum(MagicMock):
  @property
  def receipt_lag(self):
    return datetime.timedelta(seconds=30)


class ModeratorTest(CliTest):
  def setUp(self):
    super().setUp()
    self.forum = MockForum()
    self.game    = Game()
    self.town    = self.game.add_faction(Town())
    self.masons  = self.game.add_faction(Masonry("The Fellowship", self.town))
    self.mafia   = self.game.add_faction(Mafia("The Forces of Darkness"))
    self.frodo   = self.game.add_player("Frodo", Villager(self.masons),
                                        info={"message": "frodo@bagend.shire"})
    self.sam     = self.game.add_player("Samwise", Villager(self.masons),
                                        info={"message": "sam@samsgardening.com"})
    self.gandalf = self.game.add_player("Gandalf", Cop(self.town),
                                        info={"message": "mithrandir@meu.edu"})
    self.sauron  = self.game.add_player("Sauron", Godfather(self.mafia),
                                        info={"message": "sauron@mordor.gov"})
    time_zone = pytz.timezone("US/Pacific")
    self.moderator = Moderator(path=self.game_path,
                               game=self.game,
                               game_name="LOTR Mafia",
                               time_zone=time_zone,
                               night_end=datetime.time(hour=10, tzinfo=time_zone),
                               day_end=datetime.time(hour=22, tzinfo=time_zone),
                               forum=self.forum)
    self.moderator.forum    = self.forum
    self.moderator.get_time = MagicMock()
    self.moderator.sleep    = MagicMock()

    self.moderator.get_time.return_value = datetime.datetime.now(time_zone)

class ModeratorUnitTest(ModeratorTest):
  """These tests mock out all of Moderator's "side effect" methods."""

  def setUp(self):
    super().setUp()
    self.messages = []
    self.moderator.save                 = MagicMock()
    self.moderator.save_checkpoint      = MagicMock()
    self.moderator.send_message         = MagicMock()
    self.forum.get_messages             = MagicMock()
    self.forum.get_messages.side_effect = self.get_and_clear_messages

  def get_and_clear_messages(self, game, cutoff):
    messages = self.messages
    self.messages = []
    return messages

  def assert_sent_messages(self, calls):
    assert_equal(self.moderator.send_message.mock_calls, calls)
    self.moderator.send_message.reset_mock()

  def advance_phase(self):
    self.moderator.get_time.return_value = self.moderator.phase_end + \
                                           self.forum.receipt_lag + \
                                           datetime.timedelta(seconds=1)

  def test_simple_game(self):
    def logic():
      # Pass 1: Role and faction messages should be sent.
      subject = "LOTR Mafia: Start"
      self.assert_sent_messages([
        call(events.PUBLIC, "LOTR Mafia: Start", StartsWith("Welcome to <b>LOTR Mafia</b>.")),
        call([self.frodo],   subject, StartsWith("You are the <b>Mason Villager</b>.")),
        call([self.gandalf], subject, StartsWith("You are the <b>Town Cop</b>.")),
        call([self.sam],     subject, StartsWith("You are the <b>Mason Villager</b>.")),
        call([self.sauron],  subject, StartsWith("You are the <b>Mafia Godfather</b>.")),
        call([self.frodo, self.sam], subject, "You are The Fellowship."),
        call([self.sauron],  subject, StartsWith("You are the leader of The Forces of Darkness."))
      ])
      assert self.moderator.started

      # Pass 1.5: Sauron is confused.
      self.messages.append(Message(sender=self.sauron, subject="???", body="Help me!"))
      yield True
      self.assert_sent_messages([
        call(self.sauron, "???", Glob("*sauron: kill PLAYER*")),
      ])

      # Pass 2: Send in some action messages.
      self.messages.append(Message(sender=self.sam, subject="Mafia", body="Protect Frodo!"))
      self.messages.append(Message(sender=self.sauron, subject="Mafia", body="Sauron: Kill Frodo."))
      yield True
      self.assert_sent_messages([
        call(self.sam, "Mafia", "Invalid action.\n\n> Protect Frodo!"),
        call(self.sauron, "Mafia", "Confirmed.\n\n> Sauron: Kill Frodo."),
      ])

      # Pass 3: Advance the clock so night resolves.
      self.advance_phase()
      yield True
      self.assert_sent_messages([
        call(events.PUBLIC, "LOTR Mafia: Night 0", "Frodo, the <b>Mason Villager</b>, has died."),
        call(events.PUBLIC, "LOTR Mafia: Day 1", StartsWith("Night 0 is over. Day 1 actions are due by 10:00 PM.")),
      ])

      # Pass 4: Send in some vote messages.
      self.messages.append(Message(sender=self.sam, subject="My Vote", body="vote sauron\r\n-Sam"))
      self.messages.append(Message(sender=self.sauron, subject="Mafia", body="GRRRRRRRRR"))
      self.messages.append(Message(sender=self.sauron, subject="Mafia", body="Set will:\n\nYou'll regret this!"))
      yield True
      self.assert_sent_messages([
        call(self.sam, "My Vote", "Confirmed.\n\n> vote sauron\r\n-Sam"),
        call(events.PUBLIC, "LOTR Mafia: Day 1", "Current votes:\n  Samwise votes for Sauron."),
        call(self.sauron, "Mafia", "Invalid action.\n\n> GRRRRRRRRR"),
        call(self.sauron, "Mafia", "Confirmed.\n\n> Set will:\n\nYou'll regret this!"),
      ])

      # Pass 5: Advance the clock so day resolves.
      self.advance_phase()
      yield True
      self.assert_sent_messages([
        call(events.PUBLIC, "LOTR Mafia: Day 1",
             "Sauron, the <b>Mafia Godfather</b>, was lynched.\n\n  "
             "<h2>The Last Will And Testament of Sauron</h2>\n  "
             "You'll regret this!"),
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

class ModeratorMessageTest(ModeratorTest):
  """Test get_messages and send_messages with a mocked out forum object."""

  def setUp(self):
    super().setUp()
    self.moderator.public_cc = ["public@gmail.com"]
    self.moderator.private_cc = ["private@gmail.com"]

  def address(self, player):
    return "%s <%s>" % (player.name, player.info["message"])
