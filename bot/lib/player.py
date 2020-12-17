import random

from discord import User


class Player:
    """Switch between 2 players"""
    _current = 0
    _player1 = None
    _player2 = None
    _ai = False

    P1 = 1
    P2 = AI = 2

    def __init__(self, player1: User, player2: User = None, ai: bool = False, ):
        self._current = self.P1

        self._player1 = player1
        self._player2 = player2

        self._ai = ai

    def __str__(self):
        return self[self._current]

    def __getitem__(self, key):
        """Overloaded [] operator, returns player tag as string"""

        assert 1 <= key <= 2

        if key == 1:
            return self._player1.mention
        if key == 2 and self._ai:
            return "Pepek"
        if key == 2:
            return self._player2.mention

    def on_turn(self):
        """Return player on turn"""
        return self._current

    def get_user_on_turn(self):
        """Return user on turn"""
        if self._current == 1:
            return self._player1
        if self._current == 2:
            return self._player2

    def not_on_turn(self):
        """Return player not on turn"""
        if self._current == self.P1:
            return self.P2
        else:
            return self.P1

    def next(self):
        """Return next player on turn"""
        self._current += 1
        # Rollover back to player 1
        if self._current == 3:
            self._current = self.P1

        return self._current

    def shuffle(self):
        """Give turn to random player"""
        self._current = random.choice([self.P1, self.P2])
        return self._current
