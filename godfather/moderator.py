class Moderator(object):
  def __init__(self, *, path, game, night_end, day_end):
    self.path      = path
    self.game      = game
    self.night_end = night_end
    self.day_end   = day_end

  def run(self):
    pass

  def email(self, to, subject, contents):
    logging.info("Sending email...")
    logging.info("To: %s" % to)
    logging.info("Subject: %s" % subject)
    logging.info("Contents: %s" % contents)
