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

        if type(event) not in (TickEvent,
                                InputEvent,
                                StepGameEvent,
                                AsteroidMovedEvent
                                ):
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
                start_indice,
                end_indice,
                block_type,
                block_name,
                ):
        self.name = 'Arcade block spawned event'
        self.start_indice = start_indice
        self.end_indice = end_indice
        self.block_type = block_type
        self.block_name = block_name

    def __str__(self):
        return ('%s spawned from puzzle loc %s -> arcade loc %s' % (self.block_name,
                                    self.start_indice,
                                    self.end_indice)
                                    )


class MooncreteSpawnEvent(Event):

    def __init__(self, mooncrete, flyin_position):
        self.name = 'Mooncrete spawned event'
        self.mooncrete = mooncrete
        self.flyin_position = flyin_position


class MooncreteDestroyEvent(Event):

    def __init__(self, mooncrete):
        self.name = 'Mooncrete destroy event'
        self.mooncrete = mooncrete


class TurretSpawnedEvent(Event):

    def __init__(self, turret, flyin_position):
        self.name = 'Turret spawned event'
        self.turret = turret
        self.flyin_position = flyin_position


class TurretDestroyEvent(Event):

    def __init__(self, turret):
        self.name = 'Turret destroy event'
        self.turret = turret


class MoonscapeGeneratedEvent(Event):

    def __init__(self):
        self.name = 'Moonscape generated event'


class AsteroidSpawnedEvent(Event):

    def __init__(self, asteroid):
        self.name = 'Asteroid spawned event'
        self.asteroid = asteroid


class AsteroidMovedEvent(Event):

    def __init__(self, asteroid):
        self.name = 'Asteroid move event'
        self.asteroid = asteroid


class AsteroidDestroyEvent(Event):

    def __init__(self, asteroid):
        self.name = 'Asteroid destroy event'
        self.asteroid = asteroid


class MoonbaseDestroyEvent(Event):

    def __init__(self, position):
        self.name = 'Moonbase destroy event'
        self.position = position


class MissileSpawnedEvent(Event):

    def __init__(self, missile):
        self.name = 'Missle spawned event'
        self.missile = missile


class MissileMovedEvent(Event):

    def __init__(self, missile):
        self.name = 'Missle moved event'
        self.missile = missile

class MissileDestroyEvent(Event):

    def __init__(self, missile):
        self.name = 'Missle destroy event'
        self.missile = missile

