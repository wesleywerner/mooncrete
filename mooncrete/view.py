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
from panel import Panel
from sprites import Sprite


# Limit drawing to this many frames per second.
FPS = 30

# The region on the screen where all our drawing happens.
# This is our window size, or resolution in full-screen.
DRAW_AREA = pygame.Rect(0, 0, 800, 600)

# The region where puzzle gameplay happens.
# It is achored to the top-right of the screen.
# It hides to the right off-screen.
PUZZLE_AREA = pygame.Rect(0, 0, 500, 500)
PUZZLE_AREA.topleft = (DRAW_AREA.width - PUZZLE_AREA.width, 0)

# The region where arcade gameplay happens
#ARCADE_AREA = DRAW_AREA.copy()

# The mini mooscape lives right below the puzzle area.
# It has the same width as the puzzle, and uses the remainder draw area height.
MOONSCAPE_MINI = pygame.Rect(PUZZLE_AREA.bottomleft,
    (PUZZLE_AREA.width, DRAW_AREA.height - PUZZLE_AREA.height))

# The large moonscape scales to fit the window width.
# Its height is a ratio of the the big moonscape width & mini moonscape width:
# Its position is achored to the bottom left of the draw area.
MOONSCAPE_BIG = pygame.Rect(0, 440, DRAW_AREA.width, 160)

# The size to draw each puzzle block.
PUZZLE_BLOCK_SIZE = (PUZZLE_AREA.width / model.PUZZLE_WIDTH,
                     PUZZLE_AREA.height / model.PUZZLE_WIDTH)

# The size to draw each moonscape block.
MOONSCAPE_BLOCK_SIZE = (MOONSCAPE_BIG.width // model.MOONSCAPE_WIDTH,
                        MOONSCAPE_BIG.height // model.MOONSCAPE_HEIGHT)
MOONSCAPE_MINI_SIZE = (MOONSCAPE_MINI.width // model.MOONSCAPE_WIDTH,
                        MOONSCAPE_MINI.height // model.MOONSCAPE_HEIGHT)

# The gameplay layout has two types: Puzzle and Arcade.
# The whole of it is defined as DRAW_AREA.
#
# Puzzle:
#   The PUZZLE_AREA (A) is fixed and the score box (B) is resized to fit.
#   The mini moonscape view (C) is also resized to fit.
#
#
#   +-------+-------------+
#   |       |             |
#   | score | puzzle area |
#   |  box  |      A      |
#   |       |             |
#   |   B   +-------------+
#   |       | mini view C |
#   +-------+-------------+
#
# Arcade:
#   The ARCADE mode takes the moonscape panel C and scales it to fit
#   horizontally into the screen.
#
#   +---------------------+
#   |                     |
#   |          C          |
#   |     arcade view     |
#   +---------------------+
#   | moonscape ^  ^  ^  ^|
#   |       <             |
#   +---------------------+
#



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
        # stores moonbase sprites that get drawn onto the moonscape panel
        self.moonbase_sprites = {}
        # stores moving moonbase sprites that get drawn to the screen while
        # they are moving towards their destination
        self.moving_moonbase_sprites = {}
        self.panels = {}
        self.windowsize = None
        # True while we are busy moving panels around
        self.transitioning = False
        # a pre-rendered image of the game moonscape surface
        self.moon_surface = None

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
                moonscape = self.panels['moonscape']
                moonscape.show()
                moonscape.show_position = MOONSCAPE_MINI.topleft
                moonscape.scale(MOONSCAPE_MINI.size)
            elif event.state == STATE_PHASE3:
                self.panels['score'].hide()
                self.panels['puzzle'].hide()
                moonscape = self.panels['moonscape']
                moonscape.show()
                moonscape.show_position = MOONSCAPE_BIG.topleft
                moonscape.scale(MOONSCAPE_BIG.size)
            elif event.state == STATE_HELP:
                # TODO show the help panel
                pass
            elif event.state == STATE_MENU:
                self.panels['score'].hide()
                self.panels['puzzle'].hide()
                self.panels['moonscape'].hide()

        elif isinstance(event, MoonscapeGeneratedEvent):
            self.prerender_moonscape()
            self.draw_moonscape()

        elif isinstance(event, ArcadeBlockSpawnedEvent):
            # the event positions are measured in board indices.
            # translate them into screen coordinates.
            start_pos = self.translate_from_puzzle_coords(event.start_indice)
            end_pos = self.translate_from_moonscape_coords(event.end_indice)
            # these are still relative to their respective panels.
            # add the panel offsets.
            start_pos = self.translate_to_screen(
                start_pos, self.panels['puzzle'].rect.topleft
                )
            end_pos = self.translate_to_screen(
                end_pos, self.panels['moonscape'].rect.topleft
                )
            # create this sprite object
            self.create_moonbase_sprite(
                event.end_indice,
                start_pos,
                end_pos,
                event.block_type,
                event.name
                )

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
        puzzle_panel.show_position = PUZZLE_AREA.topleft
        # and it hides to the right, off-screen
        puzzle_panel.hide_position = (DRAW_AREA.width, 0)
        puzzle_panel.hide(instant=True)
        self.panels['puzzle'] = puzzle_panel

        moonscape_panel = Panel(MOONSCAPE_BIG.size, DRAW_AREA)
        # start of as a mini moonscape view
        moonscape_panel.show_position = MOONSCAPE_MINI.topleft
        # hide it by moving it down outside the draw area
        moonscape_panel.hide_position = (MOONSCAPE_MINI.left, DRAW_AREA.height + 1)
        moonscape_panel.hide(instant=True)
        self.panels['moonscape'] = moonscape_panel
        #puzzle_panel.scale((150, 150), instant=False)


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
        self.image.fill((0, 0, 0))

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
            self.draw_moonscape()

        # animate moonbase sprites.
        # before drawing the panels, as these live on one of the panels.
        self.animate_moonbases()

        # update panels
        self.transitioning = False
        for key, panel in self.panels.items():
            if panel.draw(self.image):
                self.transitioning = True

        # moving moonbases are draw on top of all other panels
        self.draw_moving_moonbases()

        pix = self.smallfont.render(
            'Mooncrete -- press space to play',
            False, color.white, color.magenta)
        pix.set_colorkey(color.magenta)
        self.image.blit(pix, (15, 15))
        self.screen.blit(self.image, DRAW_AREA)
        pygame.display.flip()

    def translate_from_puzzle_coords(self, position):
        return (position[0] * PUZZLE_BLOCK_SIZE[0],
                position[1] * PUZZLE_BLOCK_SIZE[1])

    def translate_from_moonscape_coords(self, position):
        return (position[0] * MOONSCAPE_MINI_SIZE[0],
                position[1] * MOONSCAPE_MINI_SIZE[1])

    def translate_to_screen(self, position, container_position):
        return (position[0] + container_position[0],
                position[1] + container_position[1])

    def translate_from_screen(self, position, container_position):
        return (position[0] - container_position[0],
                position[1] - container_position[1])

    def draw_puzzle_blocks(self):
        pan = self.panels['puzzle']
        pan.image.fill(color.darker_gray)
        for x, y, v in self.model.puzzle_board_data():
            if v:
                rect = pygame.Rect(
                    self.translate_from_puzzle_coords((x, y)),
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

    def draw_moving_moonbases(self):
        """
        Draws any moving moonbase sprites.
        When they reach their destination, they will be moved to the
        moonbase_sprites list where they are then drawn onto the moonscape
        panel itself.

        """

        t = pygame.time.get_ticks()
        remove_list = []
        for key, sprite in self.moving_moonbase_sprites.items():
            sprite.update(t)
            self.image.blit(sprite.image, sprite.rect)
            if not sprite.is_moving:
                # set new sprite position relative to the moonscape panel.
                # we reuse the stored indice positions for this.
                sprite.rect.topleft = (
                    sprite.moonscape_index_position[0] * MOONSCAPE_BLOCK_SIZE[0],
                    sprite.moonscape_index_position[1] * MOONSCAPE_BLOCK_SIZE[1],
                    )
                self.moonbase_sprites[key] = sprite
                remove_list.append(key)
        # remove unmoving sprites
        for remove_key in remove_list:
            del self.moving_moonbase_sprites[remove_key]

    def animate_moonbases(self):
        """
        Draw animating moonbase sprites.

        """

        t = pygame.time.get_ticks()
        pan = self.panels['moonscape']
        for key, sprite in self.moonbase_sprites.items():
            sprite.update(t)
            pan.image.blit(sprite.image, sprite.rect)

    def prerender_moonscape(self):
        """
        Draw the moonscape from the model.

        """

        self.moon_surface = pygame.Surface(MOONSCAPE_BIG.size)
        self.moon_surface.set_colorkey(color.magenta)
        self.moon_surface.fill(color.magenta)

        draw_w = MOONSCAPE_BIG.width // model.MOONSCAPE_WIDTH
        draw_h = MOONSCAPE_BIG.height // model.MOONSCAPE_HEIGHT
        for x, y, v in self.model.moonscape_data():
            if v:
                rect = pygame.Rect(
                    (x * draw_w, y * draw_h),
                    (draw_w, draw_h)
                    )
                pygame.draw.rect(self.moon_surface, (128, 128, 128), rect)

    def draw_moonscape(self):
        """
        Assemble the moonscape image.

        """

        # clear
        # draw moon base sprites
        # draw the pre-rendered moon surface
        # draw the composite on our the moonscape panel

        pan = self.panels['moonscape']
        pan.image.fill(color.magenta)

        if self.moon_surface:
            pan.image.blit(self.moon_surface, (0, 0))

    def create_moonbase_sprite(
                        self,
                        index_position,
                        start_position,
                        end_position,
                        block_type,
                        name,
                        ):
        """
        Create a moonbase object sprite.

        index_position is the (x, y) indices in the model space.
        start and end position are the screen pixels.

        """

        trace.write('creating moonbase sprite %s at position %s -> %s' %
            (index_position, start_position, end_position))
        rect = pygame.Rect(start_position, MOONSCAPE_BLOCK_SIZE)
        sprite = Sprite(name, rect)
        # store the moonscape index position for reuse
        sprite.moonscape_index_position = index_position

        # use a placehold image
        pix = pygame.Surface(MOONSCAPE_BLOCK_SIZE)
        pix.fill(color.gold)

        sprite.addimage(pix, 1, -1)
        sprite.set_position(end_position, shift_speed=4)
        # TODO set the sprite draw size to scale with the mini moonbase size.
        # or not? see how it looks.

        # store this sprite using its (x, y) as a unique id
        self.moving_moonbase_sprites[index_position] = sprite
