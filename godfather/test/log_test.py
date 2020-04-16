import pickle

from .cli_test import *

class LogTest(CliTest):

  def test_log(self):
    """Test that 'log' prints game.log."""
    exec_godfather(["init"])
    exec_godfather(["run", "--setup_only"])

    moderator = pickle.load(open(self.game_path, "rb"))
    moderator.game.log = "Bananas"
    pickle.dump(moderator, open(self.game_path, "wb"))

    result = exec_godfather(["log"])
    self.assertEqual("Bananas\n", result)
