import click
import functools
import jinja2
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

@click.group()
def main():
  pass

class Lock(object):
  def __init__(self, game_dir):
    self.lock_file = os.path.join(game_dir, "game.lock")

  def __enter__(self):
    """Lock the game directory."""
    if os.path.isfile(self.lock_file):
      raise click.ClickException(
        "Game lock is already held. " \
        "Delete %s if you're sure nothing else is using it." % self.lock_file
      )
    else:
      open(self.lock_file, "a").close()

  def __exit__(self, type, value, traceback):
    """Unlock game directory."""
    os.remove(self.lock_file)

def standard_options(*, game_dir_must_exist=True, lock_required=True):
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
    def wrapper(verbose, *, game_dir, **kwargs):
      # Configure logging.
      level = logging.DEBUG if verbose else logging.INFO
      logging.basicConfig(level=level,
                          format="%(asctime)s %(message)s",
                          datefmt="%Y-%m-%d %H:%M:%S:")

      # Run the actual command.
      if lock_required:
        with Lock(game_dir):
          f(game_dir=game_dir, **kwargs)
      else:
        f(game_dir=game_dir, **kwargs)

    return wrapper
  return decorator

def load_game(game_path, load_from=None):
  # Load game.pickle and check that it's valid.
  try:
    moderator = pickle.load(open(load_from or game_path, "rb"))
    if not isinstance(moderator, Moderator):
      raise click.ClickException("'%s is not a Moderator object." % game_path)
    moderator.path = game_path
    return moderator
  except pickle.UnpicklingError:
    raise click.ClickException("%s is not a valid game file." % game_path)

@standard_options(game_dir_must_exist=False, lock_required=False)
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
    setup_template_path = os.path.join(os.path.dirname(__file__), "templates/setup.py")
    setup_template = jinja2.Template(open(setup_template_path).read())
    open(setup_path, "w").write(setup_template.render(
      setup_seed=random.randint(0, 2**31),
      game_seed=random.randint(0, 2**31),
    ))

@standard_options()
@click.option("--setup_only", is_flag=True,
              help="Create the game.pickle file without running anything.")
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

  # Create backup directory if it doesn't exist.
  backup_dir = os.path.join(game_dir, "backups")
  logging.info("Creating %s..." % backup_dir)
  os.makedirs(backup_dir, exist_ok=True)

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
                          moderator_name=setup.moderator_name,
                          domain=setup.domain,
                          public_cc=setup.public_cc,
                          private_cc=setup.private_cc,
                          time_zone=setup.time_zone,
                          night_end=setup.night_end,
                          day_end=setup.day_end,
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

  moderator.phase_end = datetime.datetime.now(moderator.time_zone) - MAIL_DELIVERY_LAG
  set_cancelled(True)
  moderator.run()

@standard_options(lock_required=False)
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

@standard_options()
@click.option("--backup", type=str, required=True, help="The game file to restore.")
def restore(game_dir, backup):
  """Overwrite the game.pickle file with the given backup."""

  game_path = os.path.join(game_dir, "game.pickle")
  moderator = load_game(game_path, load_from=backup)
  moderator.save()
