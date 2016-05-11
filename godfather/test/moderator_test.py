import datetime
import os
import pickle
import pluginbase
import unittest

from .cli_test import *
from mafia import *
from unittest.mock import call, MagicMock

from ..moderator import *

class ModeratorTest(CliTest):
  def setUp(self):
    super().setUp()
    self.mocks   = MagicMock()
    self.game    = Game()
    self.town    = self.game.add_faction(Town())
    self.masons  = self.game.add_faction(Masonry("Fellowship", self.town))
    self.mafia   = self.game.add_faction(Mafia("Forces of Darkness"))
    self.frodo   = self.game.add_player("Frodo", Villager(self.masons),
                                        info={"email": "frodo@shire.gov"})
    self.sam     = self.game.add_player("Samwise", Villager(self.masons),
                                        info={"email": "sam@samsgardening.com"})
    self.gandalf = self.game.add_player("Gandalf", Cop(self.town),
                                        info={"email": "mithrandir@meu.edu"})
    self.sauron  = self.game.add_player("Sauron", Godfather(self.mafia),
                                        info={"email": "sauron@mordor.gov"})
    self.moderator = Moderator(path=self.game_path,
                               game=self.game,
                               name="LOTR Mafia",
                               night_end=datetime.time(hour=10),
                               day_end=datetime.time(hour=22),
                               mailgun_key="Fake Key")
    self.moderator.get_time = self.mocks.get_time = MagicMock()
    self.moderator.mailgun  = self.mocks.mailgun  = MagicMock()
    self.moderator.sleep    = self.mocks.sleep    = MagicMock()

    self.moderator.get_time.return_value = datetime.datetime.now()

  def test_send_email(self):
    pass  # Placeholder

  def test_get_emails(self):
    pass  # Placeholder

class ModeratorUnitTest(ModeratorTest):
  def setUp(self):
    super().setUp()
    self.moderator.save       = self.mocks.save       = MagicMock()
    self.moderator.send_email = self.mocks.send_email = MagicMock()
    self.moderator.get_emails = self.mocks.get_emails = MagicMock()

  def test_start(self):
    self.moderator.run(setup_only=True)

    subject        = "LOTR Mafia: Start"
    cop_role       = "You are the Town Cop.\n\nYou may investigate one player each night. You discover their alignment. Good means pro-town, Evil means Mafia or Third Party.\n\n---------------------------------------\nYou may send me the following commands:\n- investigate PLAYER"
    godfather_role = "You are the Mafia Godfather.\n\nYou appear innocent to cop investigations."
    mason_role     = "You are the Mason Villager.\n\nYou have no special abilities."
    mason_faction  = "Frodo and Samwise, you are the Fellowship."
    assert_equal(self.moderator.send_email.mock_calls, [
      call([self.frodo], subject, mason_role),
      call([self.gandalf], subject, cop_role),
      call([self.sam], subject, mason_role),
      call([self.sauron], subject, godfather_role),
      call([self.frodo, self.sam], subject, mason_faction),
    ])
    assert_equal(self.moderator.save.mock_calls, [call()])
    assert self.moderator.started

  def test_simple_game(self):
    def logic():
      # Pass 1: Role and faction emails should be sent.
      assert_equal(len(self.moderator.send_email.mock_calls), 5)
      self.moderator.send_email.reset_mock()

      # Pass 2: Send in some action emails.
      self.moderator.get_emails.return_value = [
        Email(sender=self.sam, subject="Mafia", body="Protect Frodo!"),
        Email(sender=self.sauron, subject="Mafia", body="Sauron: Kill Frodo."),
      ]
      yield True
      assert_equal(self.moderator.send_email.mock_calls, [
        call(self.sam, "Mafia", "No actions available.\n\n> protect frodo"),
      ])

      # Pass 3: Advance the clock so night resolves.
      self.moderator.get_time.return_value = self.moderator.phase_end + \
                                             datetime.timedelta(seconds=1)
      yield True
      night0 = self.game.log[-1].phase
      assert_equal(self.game.log.phase(night0), mafia.Log([
        mafia.events.Visited(self.sauron, self.frodo),
        mafia.events.Died(self.frodo),
      ], phase=night0))

      # Exit
      yield False
      yield "Foobar"

    l = logic()
    self.moderator.sleep.side_effect = l
    self.moderator.run()
    assert_equal(next(l), "Foobar")

  def test_get_next_occurrence(self):
    now  = datetime.datetime(year=2001, month=1, day=1, hour=11)
    time = datetime.time(hour=12)
    next = datetime.datetime(year=2001, month=1, day=1, hour=12)
    assert_equal(next, self.moderator.get_next_occurrence(now, time))

    now  = datetime.datetime(year=2001, month=1, day=1, hour=13)
    time = datetime.time(hour=12)
    next = datetime.datetime(year=2001, month=1, day=2, hour=12)
    assert_equal(next, self.moderator.get_next_occurrence(now, time))
