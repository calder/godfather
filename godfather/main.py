import click
import functools
import logging
import mafia
import os
import pickle
import pluginbase
import pytz
import random
import threading

from .moderator import *
from .server import *

SETUP_TEMPLATE = """
\"\"\"This file defines the game setup.

It will be imported and the following variables read:
  game_name:      The name of the game as it appears in email subjects.
  moderator_name: The name of the sender for all moderator emails.
  domain:         The domain to send email from.
  time_zone:      The time zone to report times in.
  night_end:      When night actions are resolved.
  day_end:        When lynch votes are resolved.
  game:           A mafia.Game object with the desired setup.
\"\"\"

import collections
import datetime
import pytz
import random

from mafia import *

# Basic game settings
game_name      = "Crypto Mafia"
moderator_name = "The Godfather"
domain         = "YourMailgunDomain.com"
time_zone      = pytz.timezone("US/Pacific-New")
night_end      = datetime.time(hour=10, minute=00, tzinfo=time_zone)
day_end        = datetime.time(hour=12, minute=15, tzinfo=time_zone)

# Random seeds
setup_seed = %(setup_seed)d
game_seed  = %(game_seed)d

# Helpers
Player = collections.namedtuple("Player", ["name", "email"])
player_index = 0
def add_player(game, role):
  global player_index, players
  player = players[player_index]
  player_index += 1
  return game.add_player(player.name, role, info={"email": player.email})

# Player list
players = [
  Player(name="Alice", email="alice@gmail.com"),
  Player(name="Bob", email="bob@gmail.com"),
  Player(name="Eve", email="eve@gmail.com"),
]
random.Random(setup_seed).shuffle(players)

# Game setup
game     = Game(seed=game_seed)
town     = game.add_faction(Town())
mafia    = game.add_faction(Mafia("NSA"))
cop      = add_player(game, Cop(town))
doctor   = add_player(game, Doctor(town))
goon     = add_player(game, Goon(mafia))
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
      level = logging.DEBUG if verbose else logging.INFO
      logging.basicConfig(level=level,
                          format="%(asctime)s %(message)s",
                          datefmt="%Y-%m-%d %H:%M:%S:")
      f(*args, **kwargs)
    return wrapper
  return decorator

def load_game(game_path):
  # Load game.pickle and check that it's valid.
  try:
    moderator = pickle.load(open(game_path, "rb"))
    if not isinstance(moderator, Moderator):
      raise click.ClickException("'%s is not a Moderator object." % game_path)
    moderator.path = game_path
    return moderator
  except pickle.UnpicklingError:
    raise click.ClickException("%s is not a valid game file." % game_path)

@standard_options(game_dir_must_exist=False)
def init(game_dir):
  """Initialize the game directory."""

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
      "setup_seed":  random.randint(0, 2**31),
      "game_seed":   random.randint(0, 2**31),
    })

@standard_options()
@click.option("--setup_only", is_flag=True)
def run(game_dir, setup_only):
  """Run the game to completion or ctrl-c, saving checkpoints regularly."""

  # Get Mailgun key.
  mailgun_key_path = os.path.expanduser("~/.config/godfather/mailgun_key.txt")
  logging.info("Checking for %s..." % mailgun_key_path)
  if (os.path.isfile(mailgun_key_path)):
    logging.info("Loading %s..." % mailgun_key_path)
    mailgun_key = open(mailgun_key_path).read().strip()
  else:
    raise click.ClickException("Must create %s." % mailgun_key_path)

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
    moderator = Moderator(path=game_path,
                          game=setup.game,
                          game_name=setup.game_name,
                          time_zone=setup.time_zone,
                          night_end=setup.night_end,
                          day_end=setup.day_end,
                          moderator_name=setup.moderator_name,
                          domain=setup.domain,
                          mailgun_key=mailgun_key)
    pickle.dump(moderator, open(game_path, "wb"))

  # Load the moderator.
  moderator = load_game(game_path)

  if setup_only:
    return

  # Start the server.
  server = Server(moderator)
  server_thread = threading.Thread(target=server.run, daemon=True)
  server_thread.start()

  # Run the Moderator (runs until interrupted).
  moderator.run()

@standard_options()
def poke(game_dir):
  """Resolve the current stage and exit."""

  game_path = os.path.join(game_dir, "game.pickle")
  moderator = load_game(game_path)

  moderator.phase_end = datetime.datetime.now(pytz.UTC) - MAIL_DELIVERY_LAG
  set_cancelled(True)
  moderator.run()

@standard_options()
def log(game_dir):
  """Show the game log so far."""

  # Print the log if there is one.
  game_path = os.path.join(game_dir, "game.pickle")
  if not os.path.isfile(game_path):
    logging.info("%s missing, aborting." % game_path)
    return
  logging.info("Reading log from %s..." % game_path)
  moderator = pickle.load(open(game_path, "rb"))
  if len(moderator.game.log) > 0:
    print(moderator.game.log)
