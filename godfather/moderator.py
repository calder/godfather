import datetime
import logging
import mafia
import pickle
import termcolor

class Moderator(object):
  def __init__(self, *, path, game, night_end, day_end):
    self.path       = path
    self.game       = game
    self.night_end  = night_end
    self.day_end    = day_end

    self.started    = False
    self.next_event = datetime.datetime.now() + datetime.timedelta(days=1)
    self.game.log.on_append(self.event_logged)

  def run(self, *, setup_only=False):
    """Entry point. Blocks until game finishes or an interrupt is received."""
    logging.info("Moderating game...")
    if not self.started:
      self.start()
    if setup_only:
      return

  def start(self):
    """Start the game and send out role emails."""
    logging.info("Starting game...")
    self.game.begin()
    self.started = True
    self.save()

  def save(self):
    """Save the current Moderator state to disk."""
    pickle.dump(self, open(self.path, "wb"))

  def email(self, to, subject, contents):
    """Send an email to a list of players, or everyone if to=PUBLIC."""
    assert to
    if to == mafia.events.PUBLIC:
      to = self.game.all_players
    to_str = ", ".join([p.full_str() for p in to])

    logging.info("Sending email:")
    logging.info("  To:       %s" % to_str)
    logging.info("  Subject:  %s" % subject)
    logging.info("  Contents: %s" % contents)

  def event_logged(self, event):
    """Called when an event is added to the game log."""
    prefix = termcolor.colored(">>>", "yellow")
    logging.info("%s %s" % (prefix, event.colored_str()))
    if event.to:
      to = event.to
      subject = "%s: %s" % ("Mafia", event.phase)
      self.email(to, subject, event.message)
