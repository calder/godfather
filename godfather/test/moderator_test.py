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
                               night_end=datetime.time(hour=10),
                               day_end=datetime.time(hour=22))

  def test_start(self):
    self.moderator.email = MagicMock()
    self.moderator.save  = MagicMock()
    self.moderator.run(setup_only=True)

    assert_equal(self.moderator.email.mock_calls, [
      call([self.frodo], "Mafia: Start", "You are the Mason Villager."),
      call([self.sam], "Mafia: Start", "You are the Mason Villager."),
      call([self.frodo, self.sam], "Mafia: Start", "You are the Fellowship."),
    ])
    assert_equal(self.moderator.save.mock_calls, [call()])
    assert self.moderator.started
