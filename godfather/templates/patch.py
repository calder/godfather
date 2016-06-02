"""A template for making emergency modifications to the game state."""

import godfather
import mafia
import os
import pickle

game_dir = os.path.dirname(__file__)

with godfather.Lock(game_dir):
  # Load the game state.
  game_file = os.path.join(game_dir, "game.pickle")
  moderator = pickle.load(open(game_file, "rb"))
  game = moderator.game

  # DO MANIPULATION HERE

  # Save the modified game state.
  pickle.dump(moderator, open(game_file, "wb"))
