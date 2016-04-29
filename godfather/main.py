import argparse
import click
import functools
import logging
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

@click.group()
def main():
  pass

def standard_options(*, game_dir_must_exist=True):
  def decorator(f):
    @main.command()
    @click.option("-v", "--verbose", is_flag=True)
    @click.option("--game_dir",
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
def create(game_dir):
  logging.info("Creating %s..." % game_dir)
  os.makedirs(game_dir, exist_ok=True)

  setup_path = os.path.join(game_dir, "setup.py")
  logging.info("Checking for %s..." % setup_path)
  if os.path.isfile(setup_path):
    logging.info("%s already exists." % setup_path)
  else:
    logging.info("Creating %s..." % setup_path)
    open(setup_path, "w").write(SETUP_TEMPLATE)

@standard_options()
def run(game_dir):
  raise NotImplemented
