import argparse
import click
import functools
import mafia
import os

SETUP_TEMPLATE = """
from mafia import *

players = [
  "Alice",
  "Bob",
  "Eve",
]

town = Town()
mafia = Mafia("Corleones")
factions = [town, mafia]

roles = [
  Cop(town),
  Doctor(town),
  Goon(mafia),
]

game = MakeGame(seed=123, players=players, factions=factions, roles=roles)
""".strip()

def GameDir(*, exists=True):
  return click.Path(
    dir_okay=True,
    file_okay=False,
    readable=True,
    writable=True,
    exists=exists
  )

@click.group()
def main():
  pass

@main.command()
@click.option("--game_dir", type=GameDir(exists=False))
def create(game_dir):
  # Create the game directory if it doesn't exist.
  os.makedirs(game_dir, exist_ok=True)

  # Create the setup file if it doesn't exist.
  setup_path = os.path.join(game_dir, "setup.py")
  if not os.path.isfile(setup_path):
    open(setup_path, "w").write(SETUP_TEMPLATE)

@main.command()
@click.option("--game_dir", type=GameDir())
def run(game_dir):
  raise NotImplemented
