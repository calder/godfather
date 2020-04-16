import os
import pickle
import shutil

from .cli_test import *

class RestoreTest(CliTest):

  def test_restore(self):
    """Test that 'restore' restores a game file."""
    exec_godfather(["init"])
    exec_godfather(["run", "--setup_only"])

    # Create a backup file.
    backup_path = "game.pickle.bac"
    shutil.copy(self.game_path, backup_path)
    moderator = pickle.load(open(backup_path, "rb"))
    moderator.fake_member = "Bananas"
    pickle.dump(moderator, open(backup_path, "wb"))

    # Restore the backup file.
    exec_godfather(["restore", "--backup", backup_path])

    # Check that the backup file was restored.
    moderator = pickle.load(open(self.game_path, "rb"))
    self.assertEqual("Bananas", moderator.fake_member)
