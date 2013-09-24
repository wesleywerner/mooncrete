#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see http://www.gnu.org/licenses/.


# GAME STATES
# Each level consists of multiple phases.
# Reprieve is a cool down period after the arcade phase (phase 3)

STATE_MENU = -1
STATE_PHASE1 = 1
STATE_PHASE2 = 2
STATE_PHASE3 = 3
STATE_REPRIEVE = 50
STATE_LEVELDONE = 100
STATE_LOSE = -100
STATE_HELP = 42


class StateMachine(object):
    """
    A simple stack based state machine.
    I've done so many of these what is writing one more from scratch :)
    Forgive me not commenting any further here, it is pretty self
    explanitory.

    """

    def __init__(self):
        self.stack = []

    def peek(self):
        if not self.is_empty:
            return self.stack[-1]

    def pop(self):
        if not self.is_empty:
            return self.stack.pop()

    def push(self, value):
        self.stack.append(value)
        return value

    def swap(self, value):
        self.pop()
        self.push(value)

    @property
    def is_empty(self):
        return len(self.stack) == 0
