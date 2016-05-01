class Moderator(object):
  def __init__(self, *, path, game, night_end, day_end):
    self.path      = path
    self.game      = game
    self.night_end = night_end
    self.day_end   = day_end

  def run(self):
    pass
