import click
import functools
import logging
import mafia
import os
import pickle
import pluginbase
import random

from .moderator import *

SETUP_TEMPLATE = """
\"\"\"This file defines the game setup.

It will be imported and the following variables read:
  night_end: When night actions are resolved.
  day_end:   When lynch votes are resolved.
  game:      A mafia.Game object with the desired setup.
\"\"\"

import collections
import datetime
import random
from mafia import *

night_end = datetime.time(hour=10, minute=00)
day_end   = datetime.time(hour=12, minute=15)

setup_seed = %(setup_seed)d
game_seed = %(game_seed)d

PlayerInfo = namedtuple("PlayerInfo", ["name", "email"])

players = [
  PlayerInfo(name="Alice", email="alice@google.com"),
  PlayerInfo(name="Bob", email="bob@google.com"),
  PlayerInfo(name="Eve", email="eve@nsa.gov"),
]

rng = random.Random(setup_seed)
rng.shuffle(players)

game   = Game(seed=game_seed)
town   = game.add_faction(Town())
mafia  = game.add_faction(Mafia("NSA"))
cop    = game.add_player(players[0].name, Cop(town), email=players[0].email)
doctor = game.add_player(players[1].name, Doctor(town), email=players[1].email)
goon   = game.add_player(players[2].name, Goon(town), email=players[2].email)
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
    open(setup_path, "w").write(SETUP_TEMPLATE % {
      "setup_seed": random.randint(0, 2**31),
      "game_seed":  random.randint(0, 2**31),
    })

@standard_options()
@click.option("--setup_only", is_flag=True)
def run(game_dir, setup_only):
  # Create game.pickle if it doesn't exist.
  setup_path = os.path.join(game_dir, "setup.py")
  game_path = os.path.join(game_dir, "game.pickle")
  logging.info("Checking for %s..." % game_path)
  if os.path.isfile(game_path):
    logging.info("%s already exists." % game_path)
  else:
    logging.info("Loading %s..." % setup_path)
    plugin_base = pluginbase.PluginBase(package="plugins")
    plugin_source = plugin_base.make_plugin_source(searchpath=[game_dir])
    setup = plugin_source.load_plugin("setup")
    if not isinstance(setup.game, mafia.Game):
      raise click.ClickException("'game' in %s is not a mafia.Game object." % setup_path)

    logging.info("Creating %s..." % game_path)
    moderator = Moderator(game=setup.game,
                          path=game_path,
                          night_end=setup.night_end,
                          day_end=setup.day_end)
    pickle.dump(moderator, open(game_path, "wb"))

  # Load game.pickle and check that it's valid.
  try:
    moderator = pickle.load(open(game_path, "rb"))
    if not isinstance(moderator, Moderator):
      raise click.ClickException("'%s is not a Moderator object." % game_path)
  except pickle.UnpicklingError:
    raise click.ClickException("%s is not a valid game file." % game_path)

  # Run the Moderator (runs until interrupted).
  if not setup_only:
    moderator.path = game_path
    moderator.run()

@standard_options()
def log(game_dir):
  # Print the log if there is one.
  game_path = os.path.join(game_dir, "game.pickle")
  if not os.path.isfile(game_path):
    logging.info("%s missing, aborting." % game_path)
    return
  logging.info("Reading log from %s..." % game_path)
  moderator = pickle.load(open(game_path, "rb"))
  if len(moderator.game.log) > 0:
    print(moderator.game.log)
