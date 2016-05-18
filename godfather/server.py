import datetime
import flask
import pytz

# The maximum acceptable amount of time since the last email check.
MAX_LATENCY = datetime.timedelta(minutes=1)

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

  @app.route("/status")
  def status():
    errors = []
    fetched = moderator.last_fetch
    if fetched < datetime.datetime.now(pytz.UTC) - MAX_LATENCY:
      errors.append("Last email check: %s" % fetched.strftime("%I:%M %p"))
    status = 200 if len(errors) == 0 else 500
    return flask.render_template(
      "status.html",
      errors=errors,
      status=status,
    ), status

  return app
