import os
import pickle
import tempfile
import uuid

from .cli_test import CliTest
import mafia

class InitTest(CliTest):

  def test_create_game_dir(self):
    """Init should create the game directory if not present."""
    with tempfile.TemporaryDirectory() as game_dir:
      os.rmdir(game_dir)
      assert not os.path.isdir(game_dir)

      self.godfather(["init", game_dir])
      assert os.path.isdir(game_dir)
      assert os.path.isfile(os.path.join(game_dir, "setup.py"))

  def test_game_dir_exists(self):
    """Init should succeed even if the game directory already exists."""
    with tempfile.TemporaryDirectory() as game_dir:
      self.godfather(["init", game_dir])
      assert os.path.isfile(os.path.join(game_dir, "setup.py"))

  def test_setup_py(self):
    """Init should create a valid setup.py."""
    with tempfile.TemporaryDirectory() as game_dir:
      setup_path = os.path.join(game_dir, "setup.py")
      game_path = os.path.join(game_dir, "game.pickle")

      self.godfather(["init", game_dir])
      self.exec(["python3", setup_path])

      game = pickle.load(open(game_path, "rb"))
      assert isinstance(game, mafia.Game)

  def test_preexisting_setup_py(self):
    """Init should not override setup.py if present."""
    with tempfile.TemporaryDirectory() as game_dir:
      setup_path = os.path.join(game_dir, "setup.py")
      open(setup_path, "w").write("foobar")

      self.godfather(["init", game_dir])
      self.assertEqual("foobar", open(setup_path).read())
