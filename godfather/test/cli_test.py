import click.testing
import mafia
import os
import subprocess
import tempfile
import unittest

import godfather.main
from .godfather_test import *

def record_global_event(event):
  """Add a global event. Useful for testing function calls across pickling."""
  global events
  events.append("run")

def get_global_events():
  """Return all global events."""
  global events
  return events

def clear_global_events():
  """Clear all global events."""
  global events
  events = []

def check_and_clear_global_events(events):
  mafia.assert_equal(get_global_events(), events)
  clear_global_events()

class CliTest(GodfatherTest):
  """Base class for tests of the godfather command line interface."""

  def setUp(self):
    super().setUp()
    clear_global_events()
    self.game_dir_tempfile = tempfile.TemporaryDirectory()
    self.game_dir = self.game_dir_tempfile.name

  @property
  def game_path(self):
    return os.path.join(self.game_dir, "game.pickle")

  @property
  def setup_path(self):
    return os.path.join(self.game_dir, "setup.py")

def exec(command):
  """Run a command and assert that it passes."""
  result = subprocess.run(command)
  result.check_returncode()
  return result.stdout

def exec_godfather(command, *, in_process=True):
  """Run 'godfather [command]' either within the process or in a shell."""
  if in_process:
    runner = click.testing.CliRunner()
    result = runner.invoke(godfather.main.main, command + ["--verbose"])
    if result.exception:
      raise result.exception
    mafia.assert_equal(0, result.exit_code)
    return result.output
  else:
    return self.exec(["python3", "godfather"] + command)
