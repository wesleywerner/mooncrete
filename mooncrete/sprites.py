import random
import pygame
from pygame.locals import *
import color
import helper


class MoonbaseSprite(pygame.sprite.Sprite):
    """
    A basic moonbase sprite that has a destination point which it moves to.

    """

    def __init__(self):

        super(MoonbaseSprite, self).__init__()
        self.name = 'moonbase'
        self.rect = None
        self.image = None
        self._destination = None
        self._fps = 30
        self._delay = 1000 / self._fps
        self._last_update = 0

    @property
    def fps(self):
        return self._fps

    @fps.setter
    def fps(self, value):
        self._delay = 1000 / value

    def can_update(self, ticks):
        """
        Tests if the time passed since the last update is greater than
        the fps delay.

        Use this call inside self.update() for frame rotation / animation.

        """

        if (ticks - self._last_update) > self._delay:
            self._last_update = ticks
            return True

    @property
    def is_moving(self):
        """
        Test if this sprite is busy moving to a destination position.

        """

        if self._destination:
            return self.rect.topleft != self._destination.topleft

    @property
    def destination(self):
        return self._destination

    @destination.setter
    def destination(self, position):
        if position and type(position) is tuple:
            position = pygame.Rect(position, self.rect.size)
        self._destination = position

    def move_sprite(self):
        """
        Move this sprite towards a destination.

        """

        if self._destination:
            x_diff = self._destination.left - self.rect.left
            y_diff = self._destination.top - self.rect.top
            self.rect = self.rect.move(x_diff // 5, y_diff // 5)
            if (abs(x_diff) < 5) and (abs(y_diff) < 5):
                self.rect = self._destination

    def update(self, ticks):
        """
        Update the sprite.

        """

        self.move_sprite()

        #if self.can_update(ticks):
            # do frame rotation or animation now

    def draw(self, target):
        """
        Draw us on the target surface.

        """

        if self.image and self.rect:
            target.blit(self.image, self.rect)


class AsteroidSprite(MoonbaseSprite):
    """
    An asteroid sprite that tumbles as it falls.

    """

    def __init__(self):
        super(AsteroidSprite, self).__init__()
        self.name = 'asteroid'
        self.rect = None
        self.original_image = None
        self.image = None
        self.angle = 0.0
        self.rotate_speed = random.randint(6, 25)

    def update(self, ticks):
        if self.can_update(ticks):
            self.angle = (self.angle + self.rotate_speed) % 360
            if not self.original_image:
                self.original_image = self.image.copy()
            self.image = pygame.transform.rotate(self.original_image, self.angle)
            # this magical line keeps the rotated sprite center where it was
            self.rect = self.image.get_rect(center=self.rect.center)


class MooncreteSprite(MoonbaseSprite):
    """
    A mooncrete slab that flies in from it's creation point onto the moonscape.

    """

    def __init__(self, rect):

        super(MooncreteSprite, self).__init__()
        self.name = 'mooncrete'
        self.rect = rect
        self.image = None
        self.destination = None

    def update(self, t):
        """
        Update the sprite position.

        """

        self.move_sprite()


class MissileSprite(MoonbaseSprite):
    """
    Flying ordinance that points towards the angle it is travelling.

    """

    def __init__(self, rect, image):

        super(MissileSprite, self).__init__()
        self.name = 'missile'
        self.rect = rect
        self.image = image

    def update(self, ticks):
        pass
        #if self.can_update(ticks):
            #pass


class ExplosionSprite(MoonbaseSprite):
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

    def update(self, ticks):
        pass
        #if self.can_update(ticks):
            #pass


class TurretSprite(MoonbaseSprite):
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
        self.rect = rect
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

    #def subsurface_base_images(self, surface, rect_list):
        #"""
        #Set all the base images from a list of rects and a source surface.

        #"""

        #self.base_images = []
        #for rect in rect_list:
            #self.base_images.append(surface.subsurface(rect))

    #def subsurface_turret_images(self, surface, rect_list):
        #"""
        #Set all the turret images from a list of rects and a source surface.

        #"""

        #self.turret_images = []
        #for rect in rect_list:
            #self.turret_images.append(surface.subsurface(rect))

    def update(self, ticks):
        """
        Update the sprite animation if enough time has passed.
        t would be pygame.time.get_ticks().

        """

        self.move_sprite()

        if self.can_update(ticks):

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


class MessageSprite(MoonbaseSprite):
    """
    Shows moving words on the screen with a time limit.

    """

    def __init__(self, message, font, timeout, forecolor,
                backcolor=color.black,
                draw_border=True
                ):
        super(MessageSprite, self).__init__()
        text = font.render(message, False, forecolor, color.magenta)
        text.set_colorkey(color.magenta)
        # create a slightly larger new image
        rect = text.get_rect().copy()
        rect = rect.inflate(10, 10)
        rect.topleft = (0, 0)
        self.image = pygame.Surface(rect.size)
        self.image.fill(backcolor)
        self.image.set_colorkey(color.magenta)
        # draw a border
        if draw_border:
            pygame.draw.rect(self.image, color.white, rect.inflate(-1, -1), 4)
            pygame.draw.rect(self.image, color.light_gray, rect.inflate(-5, -5), 4)
        # overlay the text
        center = text.get_rect(center=rect.center)
        self.image.blit(text, center.topleft)
        self.rect = self.image.get_rect()
        self.timeout = timeout
        self.time_passed = 0

    @property
    def expired(self):
        return (self.timeout <= 0)

    def update(self, ticks):
        if self.can_update(ticks):
            self.move_sprite()
        # each second passed reduce the timeout
        if (ticks - self.time_passed > 1000):
            self.time_passed = ticks
            self.timeout -= 1


class NumberCounterSprite(MoonbaseSprite):
    """
    Shows a counter that increments until max is reached.

    """

    def __init__(self, rect, start, maximum, font, forecolor):
        super(NumberCounterSprite, self).__init__()
        self.rect = rect
        self.value = start
        self.maximum = maximum
        self.font = font
        self.forecolor = forecolor
        self.fps = 30
        self._refresh_image()

    def update(self, ticks):
        if self.can_update(ticks):
            if self.value < self.maximum:
                self.value += 5
                if self.value > self.maximum:
                    self.value = self.maximum
                self._refresh_image()

    def _refresh_image(self):
        self.image = self.font.render(
            str(self.value), False, self.forecolor, color.magenta)
        self.image.set_colorkey(color.magenta)
