import argparse
import click
import functools
import logging
import mafia
import os
import pickle
import pluginbase

import mafia

SETUP_TEMPLATE = """
from mafia import *

players = [
  "Alice",
  "Bob",
  "Eve",
]

town = Town()
mafia = Mafia("Corleones")

roles = [
  Cop(town),
  Doctor(town),
  Goon(mafia),
]
factions = sorted(set([role.faction for role in roles]))

game = new_game(seed=123, players=players, factions=factions, roles=roles)
""".strip()

@click.group()
def main():
  pass

def standard_options(*, game_dir_must_exist=True):
  def decorator(f):
    @main.command()
    @click.option("-v", "--verbose", is_flag=True)
    @click.argument("game_dir",
                    type=click.Path(dir_okay=True,
                                    file_okay=False,
                                    readable=True,
                                    writable=True,
                                    exists=game_dir_must_exist))
    @functools.wraps(f)
    def wrapper(verbose, *args, **kwargs):
      level = logging.INFO if verbose else logging.WARNING
      logging.basicConfig(level=level,
                          format="%(asctime)s %(message)s",
                          datefmt="%Y-%m-%d %H:%M:%S:")
      f(*args, **kwargs)
    return wrapper
  return decorator

@standard_options(game_dir_must_exist=False)
def init(game_dir):
  # Create game directory if it doesn't exist.
  logging.info("Creating %s..." % game_dir)
  os.makedirs(game_dir, exist_ok=True)

  # Create setup.py file if it doesn't exist.
  setup_path = os.path.join(game_dir, "setup.py")
  logging.info("Checking for %s..." % setup_path)
  if os.path.isfile(setup_path):
    logging.info("%s already exists." % setup_path)
  else:
    logging.info("Creating %s..." % setup_path)
    open(setup_path, "w").write(SETUP_TEMPLATE)

@standard_options()
def run(game_dir):
  # Create game.pickle file if it doesn't exist.
  setup_path = os.path.join(game_dir, "setup.py")
  game_path = os.path.join(game_dir, "game.pickle")
  logging.info("Checking for %s..." % game_path)
  if os.path.isfile(game_path):
    logging.info("%s already exists." % game_path)
  else:
    logging.info("Loading %s..." % setup_path)
    plugin_base = pluginbase.PluginBase(package="setup")
    plugin_source = plugin_base.make_plugin_source(searchpath=[game_dir])
    setup = plugin_source.load_plugin("setup")
    if not isinstance(setup.game, mafia.Game):
      raise click.ClickException("'game' in %s is not a mafia.Game object." % setup_path)
    logging.info("Creating %s..." % game_path)
    pickle.dump(setup.game, open(game_path, "wb"))

@standard_options()
def log(game_dir):
  game_path = os.path.join(game_dir, "game.pickle")
  if not os.path.isfile(game_path):
    logging.info("%s missing, aborting." % game_path)
    return
  logging.info("Reading log from %s..." % game_path)
  game = pickle.load(open(game_path, "rb"))
  if len(game.log) > 0:
    print(game.log)
