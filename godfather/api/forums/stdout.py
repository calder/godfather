import datetime

from godfather.api.forum import Forum

class Stdout(Forum):
  @property
  def receipt_lag(self):
    return datetime.timedelta()

  def send_message(self, game, message):
    print(message)

  def get_messages(self, game, cutoff):
    return []
