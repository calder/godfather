import os
import pickle
import pluginbase
import unittest

from .cli_test import *
from mafia import *
from ..moderator import *

class ModeratorTest(CliTest):

  def setUp(self):
    super().setUp()
    self.game   = Game()
    self.town   = self.game.add_faction(Town())
    self.masons = self.game.add_faction(Masonry("The Fellowship", self.town))
    self.mafia  = self.game.add_faction(Mafia("The Forces of Darkness"))
    self.frodo  = self.game.add_player("Frodo", Villager(self.masons))
    self.sam    = self.game.add_player("Samwise", Villager(self.masons))
    self.moderator = Moderator(path=self.game_path,
                               game=self.game,
                               night_end=datetime.time(hour=10),
                               day_end=datetime.time(hour=22))

  def test_start(self):
    self.moderator.run(setup_only=True)
    assert self.moderator.started
    assert_equal(self.game.log, Log([
      events.RoleAnnouncement(self.frodo, self.frodo.role),
      events.RoleAnnouncement(self.sam, self.sam.role),
      events.FactionAnnouncement(self.masons, [self.frodo, self.sam]),
    ], phase=START))
