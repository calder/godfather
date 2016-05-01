import datetime
import mafia
import os
import pickle
import pluginbase
import tempfile
import uuid

from .cli_test import CliTest

class InitTest(CliTest):

  def test_create_game_dir(self):
    """'init' should create the game directory if not present."""
    with tempfile.TemporaryDirectory() as game_dir:
      os.rmdir(game_dir)
      assert not os.path.isdir(game_dir)

      self.godfather(["init", game_dir])
      assert os.path.isdir(game_dir)
      assert os.path.isfile(os.path.join(game_dir, "setup.py"))

  def test_game_dir_exists(self):
    """'init' should succeed even if the game directory already exists."""
    with tempfile.TemporaryDirectory() as game_dir:
      self.godfather(["init", game_dir])
      assert os.path.isfile(os.path.join(game_dir, "setup.py"))

  def test_setup_py(self):
    """'init' should create a valid setup.py."""
    with tempfile.TemporaryDirectory() as game_dir:
      setup_path = os.path.join(game_dir, "setup.py")
      game_path = os.path.join(game_dir, "game.pickle")

      self.godfather(["init", game_dir])

      plugin_base = pluginbase.PluginBase(package="plugins")
      plugin_source = plugin_base.make_plugin_source(searchpath=[game_dir])
      setup = plugin_source.load_plugin("setup")
      assert isinstance(setup.game, mafia.Game)
      assert isinstance(setup.night_end, datetime.time)
      assert isinstance(setup.day_end, datetime.time)

  def test_preexisting_setup_py(self):
    """'init' should not override setup.py if present."""
    with tempfile.TemporaryDirectory() as game_dir:
      setup_path = os.path.join(game_dir, "setup.py")
      open(setup_path, "w").write("foobar")

      self.godfather(["init", game_dir])
      self.assertEqual("foobar", open(setup_path).read())
