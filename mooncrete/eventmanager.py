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
                                AsteroidMovedEvent,
                                MissileMovedEvent,
                                ExplosionGrowEvent,
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


class ResetGameEvent(Event):
    """
    Signals the game is resetting.
    Clear any resources from any previous games.

    """

    def __init__(self):
        self.name = 'Reset game event'


class StepGameEvent(Event):

    def __init__(self):
        self.name = 'Step game event'


class LunarLandscapeClearedEvent(Event):

    def __init__(self):
        self.name = 'Lunar landscape cleared event'


class LunarLandSpawnEvent(Event):

    def __init__(self, land):
        self.name = 'Lunar land spawn event'
        self.land = land


class MooncreteSpawnEvent(Event):

    def __init__(self, mooncrete):
        self.name = 'Mooncrete spawned event'
        self.mooncrete = mooncrete


class MooncreteDestroyEvent(Event):

    def __init__(self, mooncrete):
        self.name = 'Mooncrete destroy event'
        self.mooncrete = mooncrete


class BuildingSpawnEvent(Event):

    def __init__(self, building):
        self.name = 'Building spawn event'
        self.building = building


class BuildingDestroyEvent(Event):

    def __init__(self, building):
        self.name = 'Building destroy event'
        self.building = building


class TurretSpawnedEvent(Event):

    def __init__(self, turret):
        self.name = 'Turret spawned event'
        self.turret = turret


class TurretDestroyEvent(Event):

    def __init__(self, turret):
        self.name = 'Turret destroy event'
        self.turret = turret


class RadarSpawnedEvent(Event):

    def __init__(self, radar):
        self.name = 'Radar spawned event'
        self.radar = radar


class RadarDestroyEvent(Event):

    def __init__(self, radar):
        self.name = 'Radar destroy event'
        self.radar = radar


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


class ExplosionSpawnEvent(Event):

    def __init__(self, explosion):
        self.name = 'Explosion spawn event'
        self.explosion = explosion


class ExplosionGrowEvent(Event):

    def __init__(self, explosion):
        self.name = 'Explosion grow event'
        self.explosion = explosion


class ExplosionDestroyEvent(Event):

    def __init__(self, explosion):
        self.name = 'Explosion destroy event'
        self.explosion = explosion


class PuzzleRowCleared(Event):

    def __init__(self, row_number):
        self.name = 'Puzzle row cleared event'
        self.row_number = row_number

    def __str__(self):

        return 'Puzzle row %s cleared' % (self.row_number,)
