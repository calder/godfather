import datetime
import os
import pickle
import pluginbase
import unittest

from unittest.mock import call, MagicMock
from .cli_test import *
from mafia import *
from ..moderator import *

class ModeratorTest(CliTest):

  def setUp(self):
    super().setUp()
    self.game   = Game()
    self.town   = self.game.add_faction(Town())
    self.masons = self.game.add_faction(Masonry("Fellowship", self.town))
    self.mafia  = self.game.add_faction(Mafia("Forces of Darkness"))
    self.frodo  = self.game.add_player("Frodo", Villager(self.masons))
    self.sam    = self.game.add_player("Samwise", Villager(self.masons))
    self.moderator = Moderator(path=self.game_path,
                               game=self.game,
                               name="LOTR Mafia",
                               night_end=datetime.time(hour=10),
                               day_end=datetime.time(hour=22),
                               mailgun_key="Fake Key")

  def test_start(self):
    self.moderator.save       = MagicMock()
    self.moderator.send_email = MagicMock()
    self.moderator.run(setup_only=True)

    subject = "LOTR Mafia: Start"
    assert_equal(self.moderator.send_email.mock_calls, [
      call([self.frodo], subject, "You are the Mason Villager."),
      call([self.sam], subject, "You are the Mason Villager."),
      call([self.frodo, self.sam], subject, "You are the Fellowship."),
    ])
    assert_equal(self.moderator.save.mock_calls, [call()])
    assert self.moderator.started

  # def test_get_emails(self):
  #   self.moderator.mailgun_key = ""
  #   self.moderator.last_fetch  = datetime.datetime(year=2016, month=1, day=1)
  #   emails = self.moderator.get_emails()
  #   print(emails)
  #   assert False

  def test_get_next_occurrence(self):
    now  = datetime.datetime(year=2001, month=1, day=1, hour=11)
    time = datetime.time(hour=12)
    next = datetime.datetime(year=2001, month=1, day=1, hour=12)
    assert_equal(next, self.moderator.get_next_occurrence(now, time))

    now  = datetime.datetime(year=2001, month=1, day=1, hour=13)
    time = datetime.time(hour=12)
    next = datetime.datetime(year=2001, month=1, day=2, hour=12)
    assert_equal(next, self.moderator.get_next_occurrence(now, time))
