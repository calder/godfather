import argparse
import click
import functools
import logging
import mafia
import os
import pickle
import random
import subprocess

SETUP_TEMPLATE = """
import os
import pickle
import random

from mafia import *

setup_seed = %(setup_seed)d
game_seed = %(game_seed)d

players = [
  "Alice",
  "Bob",
  "Eve",
]

rng = random.Random(setup_seed)
rng.shuffle(players)

game   = Game(seed=game_seed)
town   = game.add_faction(Town())
mafia  = game.add_faction(Mafia("NSA"))
cop    = game.add_player(players[0], Cop(town))
doctor = game.add_player(players[1], Doctor(town))
goon   = game.add_player(players[2], Goon(town))

path = os.path.dirname(os.path.realpath(__file__))
pickle.dump(game, open(os.path.join(path, "game.pickle"), "wb"))
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
def run(game_dir):
  # Create game.pickle file if it doesn't exist.
  setup_path = os.path.join(game_dir, "setup.py")
  game_path = os.path.join(game_dir, "game.pickle")
  logging.info("Checking for %s..." % game_path)
  if os.path.isfile(game_path):
    logging.info("%s already exists." % game_path)
  else:
    logging.info("Running %s..." % setup_path)
    subprocess.run(["python3", setup_path])

  # Check that game.pickle file is valid.
  try:
    game = pickle.load(open(game_path, "rb"))
    if not isinstance(game, mafia.Game):
      raise click.ClickException("'%s is not a mafia.Game object." % game_path)
  except pickle.UnpicklingError:
    raise click.ClickException("%s is not a valid game file." % game_path)

@standard_options()
def log(game_dir):
  # Print the log if there is one.
  game_path = os.path.join(game_dir, "game.pickle")
  if not os.path.isfile(game_path):
    logging.info("%s missing, aborting." % game_path)
    return
  logging.info("Reading log from %s..." % game_path)
  game = pickle.load(open(game_path, "rb"))
  if len(game.log) > 0:
    print(game.log)
