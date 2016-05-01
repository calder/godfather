import pickle

from .cli_test import CliTest

class LogTest(CliTest):

  def test_log(self):
    """Test that 'log' prints game.log."""
    self.godfather(["init", self.game_dir])
    self.godfather(["run", "--setup_only", self.game_dir])

    moderator = pickle.load(open(self.game_path, "rb"))
    moderator.game.log = "Bananas"
    pickle.dump(moderator, open(self.game_path, "wb"))

    result = self.godfather(["log", self.game_dir])
    self.assertEqual("Bananas\n", result)
