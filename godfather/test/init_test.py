import datetime
import mafia
import os
import pickle
import pluginbase

from .cli_test import *

class InitTest(CliTest):

  def test_create_game_dir(self):
    """'init' should create setup and patch files."""
    exec_godfather(["init"])
    assert os.path.isfile("setup.py")
    assert os.path.isfile("patch.py")

  def test_game_dir_exists(self):
    """'init' should succeed even if the game directory already exists."""
    exec_godfather(["init"])
    assert os.path.isfile("setup.py")

  def test_setup_py(self):
    """'init' should create a valid setup.py."""
    exec_godfather(["init"])

    plugin_base = pluginbase.PluginBase(package="plugins")
    plugin_source = plugin_base.make_plugin_source(searchpath=["."])
    setup = plugin_source.load_plugin("setup")
    assert isinstance(setup.game, mafia.Game)
    assert isinstance(setup.night_end, datetime.time)
    assert isinstance(setup.day_end, datetime.time)

  def test_preexisting_setup_py(self):
    """'init' should not override setup.py if present."""
    open("setup.py", "w").write("foobar")

    exec_godfather(["init"])
    self.assertEqual("foobar", open("setup.py").read())
