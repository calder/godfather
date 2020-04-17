from godfather.api.message import Message

class Forum(object):
  """A service used to send and receive messages to players."""

  @property
  def receipt_lag(self):
    """Time before we can reliably assume a message has been received."""
    raise NotImplementedError()

  def send_message(self, game, message):
    """Send a message or raise an exception if unable."""
    raise NotImplementedError()

  def get_messages(self, game, cutoff):
    """Return all messages received during the specified period."""
    raise NotImplementedError()
