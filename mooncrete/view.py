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


import os
import random
import pygame
from pygame.locals import *
import data
import trace
import color
import model
from statemachine import *
from eventmanager import *


# Limit drawing to this many frames per second.
FPS = 30

# The region on the screen where all our drawing happens.
# This is our window size, or resolution in full-screen.
DRAW_AREA = pygame.Rect(0, 0, 800, 600)

# The region where puzzle gameplay happens
PUZZLE_AREA = pygame.Rect(0, 0, 500, 500)

# The region where arcade gameplay happens
ARCADE_AREA = DRAW_AREA.copy()

# The size to draw each puzzle block.
PUZZLE_BLOCK_SIZE = (PUZZLE_AREA.width / model.PUZZLE_WIDTH,
                     PUZZLE_AREA.height / model.PUZZLE_WIDTH)

# The gameplay layout has two types: Puzzle and Arcade.
# The whole of it is defined as DRAW_AREA.
#
# Puzzle:
#   The PUZZLE_AREA (A) is fixed and the score box (B) is resized to fit.
#   The mini moonscape view (C) is also resized to fit.
#
#
#   +-------+-------------+
#   |       | PUZZLE_AREA |
#   | score |             |
#   | box   |      A      |
#   |       |             |
#   |   B   +-------------+
#   |       | mini view C |
#   +-------+-------------+


class MoonView(object):
    """
    Handles drawing a representation of the model state on screen. humbug!

    """

    def __init__(self, eventmanager, model):
        self.evman = eventmanager
        self.evman.RegisterListener(self)
        self.model = model
        self.isinitialized = False
        self.fullscreen = False
        self.screen = None
        self.clock = None
        self.font = None
        self.image = None
        self.puzzle_sprites = {}
        self.panels = {}
        self.windowsize = None
        # True while we are busy moving panels around
        self.transitioning = False

    def notify(self, event):
        """
        Called by an event in the message queue.

        """

        if isinstance(event, TickEvent):
            self.render()
            self.clock.tick(FPS)

        elif isinstance(event, InitializeEvent):
            self.initialize()

        elif isinstance(event, StateEvent):
            if event.state in (STATE_PHASE1, STATE_PHASE2):
                self.panels['score'].show()
                self.panels['puzzle'].show()
            elif event.state == STATE_PHASE3:
                self.panels['score'].hide()
                self.panels['puzzle'].hide()
                # TODO show the arcade panel
            elif event.state == STATE_HELP:
                # TODO show the help panel
                pass
            elif event.state == STATE_MENU:
                self.panels['score'].hide()
                self.panels['puzzle'].hide()

        elif isinstance(event, QuitEvent):
            self.isinitialized = False

    def initialize(self):
        """
        Set up for our visuals live here.

        """

        self.isinitialized = False
        # destroy existing screens
        if self.screen:
            pygame.display.quit()
        # initialize pygame
        result = pygame.init()
        pygame.font.init()
        self.clock = pygame.time.Clock()
        pygame.display.set_caption('Mooncrete')
        # TODO custom cursor
        pygame.mouse.set_visible(True)
        # switch the target resolution based on fullscreen mode
        target_size = DRAW_AREA.size
        flags = 0
        if self.fullscreen:
            # use native monitor resolution
            target_size = (0, 0)
            flags = FULLSCREEN
        self.screen = pygame.display.set_mode(target_size, flags)
        # TODO calculate the native res to game_area height ratio
        #       and store it for scaling the render later.
        # center the game area within the monitor
        DRAW_AREA.topleft = (
            (self.screen.get_width() - DRAW_AREA.width) / 2,
             (self.screen.get_height() - DRAW_AREA.height) / 2,)

        # load resources
        self.image = pygame.Surface(DRAW_AREA.size)

        # we are done
        self.isinitialized = True

        # load resources
        self.smallfont = pygame.font.Font(
            os.path.join('..','data','DejaVuSansMono-Bold.ttf'), 16)
        #self.background = image.load('background.png').convert()

        self.create_panels()

    def create_panels(self):
        """
        Build game panels that move around and show at various model states.

        """

        score_box_width = DRAW_AREA.width - PUZZLE_AREA.width
        score_panel = Panel((300, 600), DRAW_AREA)
        # the score panel is visible at the top-left of the screen
        score_panel.show_position = (0, 0)
        # and it hides to the left
        score_panel.hide_position = (-300, 0)
        score_panel.hide(instant=True)
        self.panels['score'] = score_panel

        puzzle_panel = Panel(PUZZLE_AREA.size, DRAW_AREA)
        # puzle grid is visible at the top-left of the screen
        puzzle_panel.show_position = (DRAW_AREA.width - PUZZLE_AREA.width, 0)
        # and it hides to the right, off-screen
        puzzle_panel.hide_position = (DRAW_AREA.width, 0)
        puzzle_panel.hide(instant=True)
        self.panels['puzzle'] = puzzle_panel

    def toggle_fullscreen(self):
        trace.write('toggling fullscreen')
        self.fullscreen = self.fullscreen ^ True
        self.initialize()

    def render(self):
        """
        Draw stuff to the screen.

        """

        if not self.isinitialized:
            # but only if we have been set up :0
            return

        state = self.model.state
        self.image.fill((0, 128, 0))

        if state == STATE_MENU:
            pass

        elif state == STATE_HELP:
            pix = self.smallfont.render(
                'help screen %s' % (self.model.player_level),
                False, color.white, color.magenta)
            pix.set_colorkey(color.magenta)
            self.image.blit(pix, (50, 150))
            pass

        elif state == STATE_LOSE:
            pass

        elif state == STATE_LEVELDONE:
            pass

        elif state in (STATE_PHASE1, STATE_PHASE2):
            self.draw_puzzle_blocks()

        elif state == STATE_PHASE3:
            pass

        # update panels
        self.transitioning = False
        for key, panel in self.panels.items():
            if panel.draw(self.image):
                self.transitioning = True

        pix = self.smallfont.render('hello, world!', False, color.white, color.magenta)
        pix.set_colorkey(color.magenta)
        self.image.blit(pix, (15, 15))
        self.screen.blit(self.image, DRAW_AREA)
        pygame.display.flip()

    def translate_view_coords(self, position):
        return (position[0] * PUZZLE_BLOCK_SIZE[0],
                position[1] * PUZZLE_BLOCK_SIZE[0])

    def draw_puzzle_blocks(self):
        pan = self.panels['puzzle']
        pan.image.fill(color.black)
        for x, y, v in self.model.puzzle_board_data():
            if v:
                rect = pygame.Rect(
                    (x * PUZZLE_BLOCK_SIZE[0], y * PUZZLE_BLOCK_SIZE[1]),
                    PUZZLE_BLOCK_SIZE
                    )
                block_color = (128, 128, 128)
                if v == model.BLOCK_CALCIUM_BARREL:
                    block_color = (0, 128, 0)
                if v == model.BLOCK_WATER_BARREL:
                    block_color = (0, 64, 0)
                if v == model.BLOCK_RADAR_BITS:
                    block_color = (128, 0, 0)
                if v == model.BLOCK_RADAR_DISH:
                    block_color = (64, 0, 0)
                if v == model.BLOCK_TURRET_AMMO:
                    block_color = (0, 0, 128)
                if v == model.BLOCK_TURRET_BASE:
                    block_color = (0, 0, 64)
                pygame.draw.rect(pan.image, block_color, rect)


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

    def draw(self, target):
        """
        Draw us on the target surface.
        Returns True if the panel is busy moving

        """

        self.move()
        if self.rect.colliderect(self._boundary):
            # only draw us if we are inside the image boundary
            target.blit(self.image, self.rect)
        return self.busy


class PuzzleBlockSprite(object):
    """
    Presents a puzzle block image with a location and sliding movement.

    """

    def __init__(self):
        self.image = pygame.Surface(PUZZLE_BLOCK_SIZE)
        self.image.set_colorkey(color.magenta)
        self.image.fill(color.white)
        self.rect = pygame.Rect((0, 0), PUZZLE_BLOCK_SIZE)

    def draw(self, target):
        target.blit(self.image, self.rect)
