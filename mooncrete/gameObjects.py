# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.


import helper


class LunarLand(object):
    """
    A lunar landscape item. It is solid and gray.

    """

    def __init__(self, position):
        self.position = position

    @property
    def id(self):
        return id(self)


class Mooncrete(object):
    """
    A slab of mooncrete.

    """

    def __init__(self, position):
        self.position = position

    @property
    def id(self):
        return self.position


class Building(object):
    """
    A moon base building.

    """

    def __init__(self, position):
        self.position = position

    @property
    def id(self):
        return self.position


class Asteroid(object):
    """
    A dangerous object that will destroy your moon base.

    """

    def __init__(self, position, destination):
        self.position = position
        self.destination = destination
        self.trajectory = list(
            reversed(helper.get_line_segments(position, destination)))

    def move(self):
        if self.trajectory:
            self.position = self.trajectory.pop()

    @property
    def id(self):
        return id(self)

    @property
    def x(self):
        return self.position[0]

    @property
    def y(self):
        return self.position[1]


class Turret(object):
    """
    A defense against incoming asteroids.

    """

    def __init__(self, position):
        self.position = position
        self.max_charge = 40
        self.charge = self.max_charge

    def recharge(self):
        if self.charge < self.max_charge:
            self.charge += 1

    @property
    def ready(self):
        return self.charge == self.max_charge

    @property
    def id(self):
        return self.position


class Radar(object):
    """
    Asteroid detector 3000.

    """

    def __init__(self, position):
        self.position = position

    @property
    def id(self):
        return self.position


class Missile(object):
    """
    Munition in transit with a designated impact point.

    """

    def __init__(self, position, destination):
        self.position = position
        self.destination = destination
        self.trajectory = helper.get_line_segments(destination, position)

    def move(self):
        if self.trajectory:
            self.position = self.trajectory.pop()
            self.trajectory = self.trajectory[:-4]
            return True

    @property
    def id(self):
        return id(self)


class Explosion(object):
    """
    An explosion from a missile detonation.
    It grows in diameter until it expires.

    """

    def __init__(self, position):
        self.position = position
        self.radius = 0.0

    def update(self):
        if self.radius < 6:
            self.radius += 0.2
            return True

    @property
    def id(self):
        return id(self)
