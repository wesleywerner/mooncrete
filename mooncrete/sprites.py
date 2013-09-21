import pygame
from pygame.locals import *
import color
import helper

# alter the Sprite class to:
#   have multiple base images
#   have multiple turret images
#   have an angle which to rotate the turret
#   limit the angle with a min and max
#   a way to cycle the angle between a range
#   a way to override the angle
#   a way to animate base images with optional loop
#   a way to animate turret images with optional loop
#   a way to set the current base image
#
#   RADARS will constantly cycle their angle and images.
#   animating base: possibly
#   animating turret: yes
#   auto angle: yes
#
#   GUN TURRETS will center their angle unless they are
#   the closest to the cursor, then their angle is overridden.
#   Their images will only animate once when told to, when a shot is fired.
#   animating base: yes, explicitly
#   animating turret: yes, explicitly
#   auto angle: yes, with override
#

class CourierSprite(pygame.sprite.Sprite):
    """
    A sprite that flies in from the puzzle area towards the mini moonscape.
    It carries the sprite object which to create in the moonscape when
    it reaches it's destination.

    """

    def __init__(self, rect, image, destination, cargo):

        super(CourierSprite, self).__init__()
        self.name = 'courier'
        self.rect = rect
        self.image = image
        self.cargo = cargo
        if destination and type(destination) is tuple:
            self.destination = pygame.Rect(destination, rect.size)
        elif type(destination) is pygame.Rect:
            self.destination = destination

    @property
    def at_destination(self):
        if self.destination:
            return self.rect.topleft == self.destination.topleft

    def update(self, t):
        """
        Update the sprite position.

        """

        if self.destination:
            x_diff = self.destination.left - self.rect.left
            y_diff = self.destination.top - self.rect.top
            self.rect = self.rect.move(x_diff // 5, y_diff // 5)
            if (abs(x_diff) < 5) and (abs(y_diff) < 5):
                self.rect = self.destination


class MooncreteSprite(pygame.sprite.Sprite):
    """
    A mooncrete slab that flies in from it's creation point onto the moonscape.

    """

    def __init__(self, rect):

        super(MooncreteSprite, self).__init__()
        self.name = 'mooncrete'
        self.rect = rect
        self.image = None
        self.destination = None

    @property
    def is_moving(self):
        """
        Test if this sprite is busy moving to a destination position.
        """

        if self.destination:
            return self.rect.topleft != self.destination.topleft

    def update(self, t):
        """
        Update the sprite position.

        """

        if self.destination:
            x_diff = self.destination.left - self.rect.left
            y_diff = self.destination.top - self.rect.top
            self.rect = self.rect.move(x_diff // 5, y_diff // 5)
            if (abs(x_diff) < 5) and (abs(y_diff) < 5):
                self.rect = self.destination

    def set_position(self, position):
        """
        Set the sprite destination to move towards
        """

        if position and type(position) is tuple:
            position = pygame.Rect(position, self.rect.size)
        self.destination = position


class MissileSprite(pygame.sprite.Sprite):
    """
    Flying ordenance that points towards the angle it is travelling.

    """

    def __init__(self, rect, image, destination):

        super(MissileSprite, self).__init__()
        self.name = 'missile'
        self.rect = rect
        self.image = image
        #self.destination = destination

        pygame.draw.line(
            self.image,
            color.white,
            (0, self.rect.height / 2),
            (self.rect.width, self.rect.height / 2),
            2)

        # calculate the angle to face our image
        self.angle = helper.angle(rect.topleft, destination)
        self.image = pygame.transform.rotate(self.image, self.angle)

    def update(self, t):
        pass


class ExplosionSprite(pygame.sprite.Sprite):
    """
    A growing explosion from some kind of detonation.

    """

    def __init__(self, position):

        super(ExplosionSprite, self).__init__()
        self.name = 'explosion'
        self.position = position
        self.rect = pygame.Rect(position, (0, 0))
        self.radius = 0.0
        self.image = None

    def grow(self, radius):
        """
        Grow the explosion sprite radius size.

        """

        if radius != self.radius:
            self.radius = radius
            half = (int(radius),) * 2
            self.rect = pygame.Rect(self.position, (radius * 2, radius * 2))
            self.rect = self.rect.move(-radius, -radius)
            self.image = pygame.Surface(self.rect.size)
            self.image.set_colorkey(color.magenta)
            self.image.fill(color.magenta)
            pygame.draw.circle(
                self.image, color.red, half, int(self.radius))

    def update(self, t):
        pass


class TurretSprite(pygame.sprite.Sprite):
    """
    A sprite with base images and a angleable turret.

    #   have multiple base images
    #   have multiple turret images
    #   have an angle which to rotate the turret
    #   limit the angle with a min and max
    #   a way to cycle the angle between a range
    #   a way to override the angle
    #   a way to animate base images with optional loop
    #   a way to animate turret images with optional loop
    #   a way to set the current base image
    #
    #   RADARS will constantly cycle their angle and images.
    #   animating base: possibly
    #   animating turret: yes
    #   auto angle: yes
    #
    #   GUN TURRETS will center their angle unless they are
    #   the closest to the cursor, then their angle is overridden.
    #   Their images will only animate once when told to, when a shot is fired.
    #   animating base: yes, explicitly
    #   animating turret: yes, explicitly
    #   auto angle: yes, with override

    """

    def __init__(self, rect):

        super(TurretSprite, self).__init__()
        self.name = 'turret'
        # the position to draw the current image
        self.rect = rect
        # the current image to draw with
        self.image = None

        # have multiple base images
        self.base_images = []
        self.base_images_current = 0
        # a way to animate base images with optional loop
        self.base_images_loop = 0

        # have multiple turret images
        self.turret_images = []
        self.turret_images_current = 0
        # a way to animate turret images with optional loop
        self.turret_images_loop = 0

        # have an angle which to rotate the turret
        self.turret_angle = 0
        # limit the angle with a min and max
        self.turret_angle_range = (0, 360)
        # a way to cycle the angle between a range
        self.turret_angle_auto_cycle = 0
        # a way to override the angle
        self.turrent_angle_override = -1

        self.fps = 10
        self._delay = 1000 / self.fps
        self._last_update = 0

        # for testing build a placeholder turret image
        timage = pygame.Surface(rect.size)
        timage.set_colorkey(color.magenta)
        timage.fill(color.magenta)
        pygame.draw.line(
            timage,
            color.white,
            (0, self.rect.height / 2),
            (self.rect.width, self.rect.height / 2),
            2)
        self.turret_images.append(timage)

    def subsurface_base_images(self, surface, rect_list):
        """
        Set all the base images from a list of rects and a source surface.

        """

        self.base_images = []
        for rect in rect_list:
            self.base_images.append(surface.subsurface(rect))

    def subsurface_turret_images(self, surface, rect_list):
        """
        Set all the turret images from a list of rects and a source surface.

        """

        self.turret_images = []
        for rect in rect_list:
            self.turret_images.append(surface.subsurface(rect))

    def canupdate(self, t):
        """
        Tests if it is time to update again
        time is the current game ticks. It is used to calculate when to update
            so that animations appear constant across varying fps.
        """

        if t - self._last_update > self._delay:
            self._last_update = t
            return True

    def update(self, t):
        """
        Update the sprite animation if enough time has passed.
        t would be pygame.time.get_ticks().

        """

        if self.canupdate(t):

            if self.turret.ready:
                self.image.fill(color.gold)
                # angle the turret
                if self.turrent_angle_override > -1:
                    angled_pix = pygame.transform.rotate(
                        self.turret_images[self.turret_images_current],
                        self.turrent_angle_override)
                    self.image.blit(angled_pix, (0, 0))
                    #self.image.blit(self.turret_images[self.turret_images_current], (0, 0))
            else:
                self.image.fill(color.gray)
                # draw a recharge bar
                charge_ratio = self.turret.charge / float(self.turret.max_charge)
                charged = int(self.rect.height * charge_ratio)
                bar = pygame.Rect(0, self.rect.height - charged, 4, charged)
                pygame.draw.rect(self.image, color.white, bar)


# KEEP THIS AS THE MOVEMENT IS NICE FOR THE MOVING MOONBASE SPRITES
class Sprite(pygame.sprite.Sprite):
    """
    Represents an animated sprite.
    """

    def __init__(self, name, rect, *groups):
        """
        rect(Rect) of the sprite on screen.
        *groups(sprite.Group) add sprite to these groups.
        """

        super(Sprite, self).__init__(*groups)
        self.name = name
        self.rect = rect
        self.image = None
        self._images = []
        self._start = pygame.time.get_ticks()
        self._delay = 0
        self._last_update = 0
        self._frame = 0
        self._hasframes = False
        self.fps = 1
        self.loop = -1
        self.destination = None

    @property
    def is_moving(self):
        """
        Test if this sprite is busy moving to a destination position.
        """

        if self.destination:
            return self.rect.topleft != self.destination.topleft

    def addimage(self, image, fps, loop):
        """
        Allows adding of a animated sprite image.
        The fps applies to all frames. It overwrites the previous fps value.
        """

        self._images.append(image)
        self._hasframes = len(self._images) > 0
        if len(self._images) > 0:
            self.image = self._images[0]
        if fps <= 0:
            fps = 1
        self._delay = 1000 / fps
        self.loop = loop
        self._frame = 0

    def clear(self):
        """
        Clear sprite images
        """

        while len(self._images) > 0:
            del self._images[-1]
        self._hasframes = False

    def canupdate(self, t):
        """
        Tests if it is time to update again
        time is the current game ticks. It is used to calculate when to update
            so that animations appear constant across varying fps.
        """

        if t - self._last_update > self._delay:
            return True

    def update(self, t):
        """
        Update the sprite animation if enough time has passed.
        t would be pygame.time.get_ticks() passed from the caller.
        Call this each game tick, either manually if this sprite is stored in a list,
        or if you keep sprites in a PyGame.Group object it will be called for you when you
        issue the Group.draw() method.
        """

        if self.destination:
            x_diff = self.destination.left - self.rect.left
            y_diff = self.destination.top - self.rect.top
            self.rect = self.rect.move(x_diff // 5, y_diff // 5)
            if (abs(x_diff) < 5) and (abs(y_diff) < 5):
                self.rect = self.destination

        if self.canupdate(t):
            self._last_update = t
            if self._hasframes:
                self._frame += 1
                if self._frame >= len(self._images):
                    self._frame = 0
                    if self.loop > 0:
                        self.loop -= 1
                    if self.loop == 0:
                        self._hasframes = False
                        self._frame = -1
                self.image = self._images[self._frame]

    def set_position(self, position):
        """
        Set the sprite destination. It will move towards this position.
        """

        if position and type(position) is tuple:
            position = pygame.Rect(position, self.rect.size)
        self.destination = position
