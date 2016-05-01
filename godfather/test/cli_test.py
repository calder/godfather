import click.testing
import os
import subprocess
import tempfile
import unittest

import godfather.main

class CliTest(unittest.TestCase):
  """Base class for tests of the godfather command line interface."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.game_dir_tempfile = tempfile.TemporaryDirectory()
    self.game_dir = self.game_dir_tempfile.name

  @property
  def game_path(self):
    return os.path.join(self.game_dir, "game.pickle")

  @property
  def setup_path(self):
    return os.path.join(self.game_dir, "setup.py")

  def exec(self, command):
    """Run a command and assert that it passes."""
    result = subprocess.run(command)
    result.check_returncode()
    return result.stdout

  def godfather(self, command, *, in_process=True):
    """Run 'godfather [command]' either within the process or in a shell."""
    if in_process:
      runner = click.testing.CliRunner()
      result = runner.invoke(godfather.main.main, command + ["--verbose"])
      print(result.output)
      if result.exception:
        raise result.exception
      self.assertEqual(0, result.exit_code)
      return result.output
    else:
      return self.exec(["python3", "godfather"] + command)
