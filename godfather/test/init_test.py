import subprocess
import tempfile
import unittest
import uuid

class InitTest(unittest.TestCase):
  def test_create_game_dir(self):
    """Init should create the game directory if not present."""
    game_dir = "/tmp/game-%s" % uuid.uuid4()
    subprocess.run(["python3", "godfather", "init"])
    print(game_dir)

  def test_game_dir_exists(self):
    """Init should succeed even if the game directory already exists."""
    pass

  def test_setup_py(self):
    """Init should create a valid setup.py."""
    with tempfile.TemporaryDirectory() as game_dir:
      pass

  def test_setup_py_exists(self):
    """Init should not override setup.py if present."""
    pass
