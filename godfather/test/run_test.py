import os
import pickle
import pluginbase
import pytest

from .cli_test import *
from ..moderator import *

def fake_run():
  record_global_event("run")

class RunTest(CliTest):

  def test_setup(self):
    """Test setup functionality of 'run'."""
    exec_godfather(["init", self.game_dir])
    assert not os.path.isfile(self.game_path)

    # 'run' should create game.pickle.
    exec_godfather(["run", "--setup_only", self.game_dir])
    assert os.path.isfile(self.game_path)
    moderator = pickle.load(open(self.game_path, "rb"))
    assert isinstance(moderator, Moderator)

    # 'run' should preserve an existing game.pickle
    moderator.test_value = 123
    pickle.dump(moderator, open(self.game_path, "wb"))
    exec_godfather(["run", "--setup_only", self.game_dir])
    moderator = pickle.load(open(self.game_path, "rb"))
    self.assertEqual(123, moderator.test_value)

  def test_moderator_run(self):
    """'run' should call Moderator.run()."""
    exec_godfather(["init", self.game_dir])
    exec_godfather(["run", "--setup_only", self.game_dir])

    # Inject a run() method we can check.
    moderator = pickle.load(open(self.game_path, "rb"))
    moderator.run = fake_run
    pickle.dump(moderator, open(self.game_path, "wb"))

    # Call 'run' and check that our run() method was called.
    exec_godfather(["run", self.game_dir])
    check_and_clear_global_events(["run"])

    # Check that 'run --setup_only' doesn't call run().
    exec_godfather(["run", "--setup_only", self.game_dir])
    check_and_clear_global_events([])

  class RunLockTestHelper(object):
    def __init__(self, game_dir):
      self.game_dir = game_dir

    def run(self):
      # Check that the game lock exists.
      assert os.path.isfile(os.path.join(self.game_dir, "game.lock"))

      # Start another 'run'. It should fail because we hold the game lock.
      with pytest.raises(SystemExit):
        exec_godfather(["run", "--setup_only", self.game_dir])

  def test_run_lock(self):
    """'run' should fail if the game dir's lock is already held."""
    exec_godfather(["init", self.game_dir])
    exec_godfather(["run", "--setup_only", self.game_dir])

    moderator = pickle.load(open(self.game_path, "rb"))
    helper = self.RunLockTestHelper(self.game_dir)
    moderator.run = helper.run
    pickle.dump(moderator, open(self.game_path, "wb"))

    # Call 'run' with our injected helper code.
    exec_godfather(["run", self.game_dir])

    # Check that the game lock was deleted.
    assert not os.path.isfile(os.path.join(self.game_dir, "game.lock"))
