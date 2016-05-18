import flask
import mafia

def Server(moderator):
  app = flask.Flask(__name__)
  game = moderator.game

  @app.route("/")
  def index():
    return "Hello!"

  @app.route("/players")
  def players():
    return flask.render_template(
      "players.html",
      players=game.players,
      all_players=game.all_players,
    )

  @app.route("/secret")
  def secret():
    return "Ooooooh!"

  return app
