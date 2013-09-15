import pygame
from pygame.locals import *
import color

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
