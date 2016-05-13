import os
import pickle
import pluginbase

from .cli_test import *
from ..moderator import *

def fake_run():
  record_global_event("run")

class RunTest(CliTest):

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
    self.godfather(["init", self.game_dir])
    self.godfather(["run", "--setup_only", self.game_dir])

    # Inject a run() method we can check.
    moderator = pickle.load(open(self.game_path, "rb"))
    moderator.run = fake_run
    pickle.dump(moderator, open(self.game_path, "wb"))

    # Call 'run' and check that our run() method was called.
    self.godfather(["run", self.game_dir])
    check_and_clear_global_events(["run"])

    # Check that 'run --setup_only' doesn't call run().
    self.godfather(["run", "--setup_only", self.game_dir])
    check_and_clear_global_events([])
