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


import math


def get_line_segments(start, end):
    """
    Returns a list of line segments that make up a line between two points.
    Returns [(x1, y1), (x2, y2), ...]

    Source: http://roguebasin.roguelikedevelopment.org/index.php?title=Bresenham%27s_Line_Algorithm

    """

    x1, y1 = start
    x2, y2 = end
    points = []
    issteep = abs(y2 - y1) > abs(x2 - x1)
    if issteep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2
    rev = False
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
        rev = True
    deltax = x2 - x1
    deltay = abs(y2 - y1)
    error = int(deltax / 2)
    y = y1
    ystep = None
    if y1 < y2:
        ystep = 1
    else:
        ystep = -1
    for x in range(x1, x2 + 1):
        if issteep:
            points.append((y, x))
        else:
            points.append((x, y))
        error -= deltay
        if error < 0:
            y += ystep
            error += deltax
    # Reverse the list if the coordinates were reversed
    if rev:
        points.reverse()
    return points

def distance(x, y, u, v):
    """
    Returns the distance between two cartesian points.
    """

    return math.sqrt((x - u) ** 2 + (y - v) ** 2)

def direction(x, y, u, v):
    """
    Returns the (x, y) offsets required to move point a (x, y)
    towards point b (u, v).

    """

    deltax = u - x
    deltay = v - y
    # theta is the angle (in radians) of the direction in which to move
    theta = math.atan2(deltay, deltax)
    # r is the distance to move
    r = 1.0
    deltax = r * math.cos(theta)
    deltay = r * math.sin(theta)
    return (int(round(deltax)), int(round(deltay)))


def clamp(n, minn, maxn):
    """
    Constrain a value within a range.

    """

    return max(min(maxn, n), minn)

def angle(pointA, pointB):
    """
    Return the angle between two points.

    """

    dx = pointB[0] - pointA[0]
    dy = pointB[1] - pointA[1]
    rads = math.atan2(-dy, dx)
    rads %= 2 * math.pi
    return math.degrees(rads)
