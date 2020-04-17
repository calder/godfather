class Message(dict):
  def __getattr__(self, attr):
    return self[attr]

  def __repr__(self):
    items = ["%s=%r" % (k, v) for k, v in self.items() if v]
    return "Message(%s)" % ", ".join(items)
