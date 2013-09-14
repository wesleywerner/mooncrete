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


import trace


class EventManager(object):

    def __init__(self):
        self.listeners = []

    def RegisterListener(self, listener):
        self.listeners.append(listener)

    def UnregisterListener(self, listener):
        if listener in self.listeners:
            self.listeners.remove(listener)

    def Post(self, event):

        if type(event) not in (TickEvent, InputEvent, StepGameEvent):
            trace.write(str(event))
        for listener in self.listeners:
            listener.notify(event)


class Event(object):

    def __init__(self):
        self.name = 'Generic event'

    def __str__(self):
        return self.name


class QuitEvent(Event):

    def __init__(self):
        self.name = 'Quit event'


class TickEvent(Event):

    def __init__(self):
        self.name = 'Tick event'


class InputEvent(Event):

    def __init__(self, char, clickpos):
        self.name = 'Input event'
        self.char = char
        self.clickpos = clickpos

    def __str__(self):
        return ('%s, char=%s, clickpos=%s' %
            (self.name, self.char, self.clickpos))


class InitializeEvent(Event):

    def __init__(self):
        self.name = 'Initialize event'


class StateEvent(Event):

    def __init__(self, state):
        self.name = 'State event'
        self.state = state

    def __str__(self):
        return ('%s: %s' % (self.name, str(self.state)))


class StepGameEvent(Event):

    def __init__(self):
        self.name = 'Step game event'


class ArcadeBlockSpawnedEvent(Event):

    def __init__(
                self,
                puzzle_block_position,
                arcade_block_position,
                block_type
                ):
        self.name = 'Arcade block spawned event'
        self.puzzle_block_position = puzzle_block_position
        self.arcade_block_position = arcade_block_position
        self.block_type = block_type

    def __str__(self):
        return ('%s: type %s from %s at %s ' % (self.name,
                                    self.block_type,
                                    self.puzzle_block_position,
                                    self.arcade_block_position)
                                    )
