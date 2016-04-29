import click.testing
import subprocess
import unittest

import godfather.main

class CliTest(unittest.TestCase):
  """Base class for tests of the godfather command line interface."""

  def exec(self, command):
    """Run a command and assert that it passes."""
    self.assertEqual(0, subprocess.run(command).returncode)

  def godfather(self, command, *, in_process=True):
    """Run 'godfather [command]' either within the process or in a shell."""
    if in_process:
      runner = click.testing.CliRunner()
      result = runner.invoke(godfather.main.main, command + ["--verbose"])
      print(result.output)
      if result.exception:
        raise result.exception
      self.assertEqual(0, result.exit_code)
    else:
      self.exec(["python3", "godfather"] + command)
