import pygame
from pygame.locals import *
import color

class Panel(object):
    """
    Provides a movable image that have hide and show positions, it
    moves towards these destinations depending on it's current state.

    """

    def __init__(self, size, boundary):
        self.size = size
        self.image = pygame.Surface(size)
        self.image.set_colorkey(color.magenta)
        self.image.fill(color.blue)
        self.background_image = None
        self.border_image = None
        # current draw position
        self.rect = pygame.Rect((0, 0), size)
        # show position
        self._show_position = pygame.Rect((0, 0), size)
        # hide position
        self._hide_position = pygame.Rect((0, 0), size)
        # are we showing or hiding
        self.showing = True
        # True while we are moving
        self.busy = False
        # the boundary where we are allowed to draw.
        self._boundary = boundary
        # the size to scale to on render. None means no scale.
        self._target_size = None
        self._current_size = size
        # the crop size to render. None means no crop.
        self._target_crop = None
        self._current_crop = size

    @property
    def show_position(self):
        return self.show_position

    @show_position.setter
    def show_position(self, value):
        if type(value) is pygame.Rect:
            self._show_position = value
        else:
            self._show_position = pygame.Rect(value, self.size)

    @property
    def hide_position(self):
        return self.hide_position

    @hide_position.setter
    def hide_position(self, value):
        if type(value) is pygame.Rect:
            self._hide_position = value
        else:
            self._hide_position = pygame.Rect(value, self.size)

    @property
    def position(self):
        return self.rect

    @position.setter
    def position(self, value):
        if type(value) is pygame.Rect:
            self.rect = value
        else:
            self.rect = pygame.Rect(value, self.size)

    @property
    def destination(self):
        if self.showing:
            return self._show_position
        else:
            return self._hide_position

    def clear(self):
        """
        Clears our image and draw the background_image on if it exists.

        """

        self.image.fill(color.magenta)
        if self.background_image:
            self.image.blit(self.background_image, (0, 0))

    def crop(self, rect, instant=False):
        """
        Set a new crop rect.
        The panel will step towards this rect (unless instant is True).

        """

        self._target_crop = rect
        if instant and size:
            self._current_crop = rect

    def scale(self, size, instant=False):
        """
        Set a new target (w, h) size.
        The panel will step towards this size (unless instant is True).

        """

        self._target_size = size
        if instant and size:
            self._current_size = size

    def show(self, instant=False):
        self.showing = True
        if instant:
            self.rect = self._show_position

    def hide(self, instant=False):
        self.showing = False
        if instant:
            self.rect = self._hide_position

    def move(self):
        """
        Update our position if necessary.

        """

        if self.rect != self.destination:
            x_diff = self.destination.left - self.rect.left
            y_diff = self.destination.top - self.rect.top
            self.rect = self.rect.move(x_diff // 5, y_diff // 5)
            if (abs(x_diff) < 5) and (abs(y_diff) < 5):
                self.rect = self.destination
            self.busy = True
        else:
            self.busy = False

    def rescale(self):
        """
        Update our scale size to match the target scale.

        """

        # if there is a scaled size set, and it does not match our current size
        if (self._target_size and (self._target_size != self._current_size)):
            # get the delta between the two and resize our current size
            # with a fraction of the delta
            w, h = self._current_size
            w_diff = self._target_size[0] - w
            h_diff = self._target_size[1] - h
            self._current_size = (w + w_diff // 5, h + h_diff // 5)
            # if the deltas get close enough to a minimum we turn off scaling
            if (abs(w_diff) < 5) and (abs(h_diff) < 5):
                self._current_size = self._target_size

    def draw(self, target):
        """
        Draw us on the target surface.
        Returns True if the panel is busy moving

        """

        self.rescale()
        self.move()
        # only draw us if we are inside the image boundary
        if self.rect.colliderect(self._boundary):
            if self._target_size:
                resized = pygame.transform.scale(self.image, self._current_size)
                target.blit(resized, self.rect)
                if self.border_image:
                    resized = pygame.transform.scale(self.border_image, self._current_size)
                    target.blit(resized, self.rect)
            else:
                target.blit(self.image, self.rect)
                if self.border_image:
                    target.blit(self.border_image, self.rect)
        return self.busy

    def point_to_screen(self, position):
        """
        Translate the given position to screen coordinates.

        """

        return (position[0] + self.rect.left, position[1] + self.rect.top)
