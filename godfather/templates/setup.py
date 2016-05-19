"""This file defines the game setup.

It will be imported and the following variables read:

  game_name:      The name of the game as it appears in email subjects.
  moderator_name: The name of the sender for all moderator emails.
  domain:         The domain to send email from.

  public_cc:      A list of emails to CC on all public emails.
  private_cc:     A list of emails to CC on all emails.

  time_zone:      The time zone to report times in.
  night_end:      When night actions are resolved.
  day_end:        When lynch votes are resolved.

  game:           A mafia.Game object with the desired setup.

For a complete list of roles, see https://github.com/calder/mafia.
"""

import collections
import datetime
import pytz
import random

from mafia import *

# Basic game settings
game_name      = "Crypto Mafia"
moderator_name = "The Godfather"
domain         = "YourMailgunDomain.com"
public_cc      = []
private_cc     = []
time_zone      = pytz.timezone("US/Pacific-New")
night_end      = datetime.time(hour=10, minute=00, tzinfo=time_zone)
day_end        = datetime.time(hour=12, minute=15, tzinfo=time_zone)

# Random seeds
setup_seed = {{ setup_seed }}
game_seed  = {{ game_seed }}

# Helpers (do not edit)
Player = collections.namedtuple("Player", ["name", "email"])
player_index = 0
def add_player(role):
  global game, player_index, players
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
cop      = add_player(Cop(town))
doctor   = add_player(Doctor(town))
goon     = add_player(Goon(mafia))

# Make sure everyone has a role
assert len(players) == len(game.players)
