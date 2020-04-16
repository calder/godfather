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
import shutil
import threading

from .moderator import *
from .server import *

GAME_PATH  = "game.pickle"
SETUP_PATH = "setup.py"

def relative_path(path):
  """Create a path relative to this file."""
  return os.path.join(os.path.dirname(__file__), path)

@click.group()
def main():
  pass

class Lock(object):
  def __init__(self):
    self.lock_file = "game.lock"

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

def standard_options(*, lock_required=True):
  def decorator(f):
    @main.command()
    @click.option("-v", "--verbose", is_flag=True)
    @functools.wraps(f)
    def wrapper(verbose, *args, **kwargs):
      # Configure logging.
      level = logging.DEBUG if verbose else logging.INFO
      logging.basicConfig(level=level,
                          format="%(asctime)s %(message)s",
                          datefmt="%Y-%m-%d %H:%M:%S:")

      # Run the actual command.
      if lock_required:
        with Lock():
          f(*args, **kwargs)
      else:
        f(*args, **kwargs)

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

@standard_options(lock_required=False)
def init():
  """Initialize the game directory."""

  # Create setup.py file if it doesn't exist.
  logging.info("Checking for %s..." % SETUP_PATH)
  if os.path.isfile(SETUP_PATH):
    logging.info("%s already exists." % SETUP_PATH)
  else:
    logging.info("Creating %s..." % SETUP_PATH)
    setup_template_path = relative_path("templates/setup.py")
    setup_template = jinja2.Template(open(setup_template_path).read())
    open(SETUP_PATH, "w").write(setup_template.render(
      setup_seed=random.randint(0, 2**31),
      game_seed=random.randint(0, 2**31),
    ))

  # Create patch.py file if it doesn't exist.
  patch_path = "patch.py"
  logging.info("Checking for %s..." % patch_path)
  if os.path.isfile(patch_path):
    logging.info("%s already exists." % patch_path)
  else:
    logging.info("Creating %s..." % patch_path)
    patch_template_path = relative_path("templates/patch.py")
    shutil.copyfile(patch_template_path, patch_path)

@standard_options()
@click.option("--setup_only", is_flag=True,
              help="Create the game.pickle file without running anything.")
def run(setup_only):
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
  backup_dir = "backups"
  logging.info("Creating %s..." % backup_dir)
  os.makedirs(backup_dir, exist_ok=True)

  # Create game.pickle if it doesn't exist.
  logging.info("Checking for %s..." % GAME_PATH)
  if os.path.isfile(GAME_PATH):
    logging.info("%s already exists." % GAME_PATH)
  else:
    logging.info("Loading %s..." % SETUP_PATH)
    plugin_base = pluginbase.PluginBase(package="plugins")
    plugin_source = plugin_base.make_plugin_source(searchpath=["."])
    setup = plugin_source.load_plugin("setup")
    if not isinstance(setup.game, mafia.Game):
      raise click.ClickException("'game' in %s is not a mafia.Game object." % SETUP_PATH)

    logging.info("Creating %s..." % GAME_PATH)
    moderator = Moderator(path=GAME_PATH,
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
    pickle.dump(moderator, open(GAME_PATH, "wb"))

  # Load the moderator.
  moderator = load_game(GAME_PATH)

  if setup_only:
    return

  # Start the server.
  server = Server(moderator)
  server_thread = threading.Thread(target=server.run, daemon=True)
  server_thread.start()

  # Run the Moderator (runs until interrupted).
  moderator.run()

@standard_options()
def resolve():
  """Resolve the current stage and exit."""

  moderator = load_game(GAME_PATH)

  moderator.phase_end = datetime.datetime.now(moderator.time_zone) - MAIL_DELIVERY_LAG
  set_cancelled(True)
  moderator.run()

@standard_options(lock_required=False)
def log():
  """Show the game log so far."""

  # Print the log if there is one.
  if not os.path.isfile(GAME_PATH):
    logging.info("%s missing, aborting." % GAME_PATH)
    return
  logging.info("Reading log from %s..." % GAME_PATH)
  moderator = pickle.load(open(GAME_PATH, "rb"))
  if len(moderator.game.log) > 0:
    print(moderator.game.log)

@standard_options()
@click.option("--backup", type=str, required=True, help="The game file to restore.")
def restore(backup):
  """Overwrite the game.pickle file with the given backup."""

  moderator = load_game(GAME_PATH, load_from=backup)
  moderator.save()
