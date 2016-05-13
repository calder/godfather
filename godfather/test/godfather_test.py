import unittest

from ..moderator import *

class GodfatherTest(unittest.TestCase):
  def setUp(self):
    super().setUp()
    set_cancelled(False)
