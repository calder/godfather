import datetime
import mafia
import os
import pickle
import pluginbase
import tempfile
import uuid

from .cli_test import CliTest
from ..moderator import *

def fake_run():
  events.append("Moderator.run()")

class RunTest(CliTest):

  def setUp(self):
    super().setUp()
    global events
    events = []

  def test_setup(self):
    """Test setup functionality of 'run'."""
    self.godfather(["init", self.game_dir])
    assert not os.path.isfile(self.game_path)

    # 'run' should create game.pickle.
    self.godfather(["run", "--setup_only", self.game_dir])
    assert os.path.isfile(self.game_path)
    moderator = pickle.load(open(self.game_path, "rb"))
    assert isinstance(moderator, Moderator)

    # 'run' should preserve an existing game.pickle
    moderator.test_value = 123
    pickle.dump(moderator, open(self.game_path, "wb"))
    self.godfather(["run", "--setup_only", self.game_dir])
    moderator = pickle.load(open(self.game_path, "rb"))
    self.assertEqual(123, moderator.test_value)

  def test_moderator_run(self):
    """'run' should call Moderator.run()."""
    global events

    self.godfather(["init", self.game_dir])
    self.godfather(["run", "--setup_only", self.game_dir])

    # Inject a run() method we can check.
    global test_path
    test_path = os.path.join(self.game_dir, "test_file.txt")
    moderator = pickle.load(open(self.game_path, "rb"))
    moderator.run = fake_run
    pickle.dump(moderator, open(self.game_path, "wb"))

    # Call 'run' and check that our run() method was called.
    self.godfather(["run", self.game_dir])
    self.assertEqual(["Moderator.run()"], events)

    # Check that 'run --setup_only' doesn't call run().
    events = []
    self.godfather(["run", "--setup_only", self.game_dir])
    self.assertEqual([], events)
