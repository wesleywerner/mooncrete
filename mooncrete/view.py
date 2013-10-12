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
import collections
import pygame
from pygame.locals import *
import data
import trace
import color
import model
from statemachine import *
from eventmanager import *
from panel import Panel
from sprites import *


# Limit drawing to this many frames per second.
FPS = 30

# The region on the screen where all our drawing happens.
# This is our window size, or resolution in full-screen.
DRAW_AREA = pygame.Rect(0, 0, 800, 600)


# PUZZLE LAYOUT
#   +-------+----------+
#   |   B   | mooncrete|
#   | score +----------+
#   |  box  |          |
#   |       |          |
#   +-------| P        |
#   |A mini | puzzle   |
#   +-------+----------+
#
# puzzle
#   fixed size (500, 500).
#   anchored to bottomright.
# mini view
#   fixed size in ratio (300, 225).
#   anchored to bottom left.
# score box
#   takes the remaining width and height.
#   fixed to topleft.

# score box position and size
SCORE_BOX = pygame.Rect(0, 0, 300, 375)

# puzzle position and size
PUZZLE_POS = pygame.Rect(0, 0, 500, 500)
PUZZLE_POS.topleft = (
    DRAW_AREA.width - PUZZLE_POS.width,
    DRAW_AREA.height - PUZZLE_POS.height)

# The size of a puzzle block is in ratio to the puzzle view size
# to the model puzzle size.
PUZZLE_BLOCK_SIZE = (
    PUZZLE_POS.width / model.PUZZLE_WIDTH,
    PUZZLE_POS.height / model.PUZZLE_HEIGHT)

# arcade position and size (takes full draw area)
ARCADE_POS = DRAW_AREA.copy()

# The size of an arcade sprite is in ratio to the arcade view size
# to the model arcade size.
ARCADE_SPRITE_SIZE = (
    ARCADE_POS.width // (model.ARCADE_WIDTH / model.BLOCK_PADDING),
    ARCADE_POS.height // (model.ARCADE_HEIGHT / model.BLOCK_PADDING))

# Game messages live inside a message panel
MESSAGE_POS = pygame.Rect(SCORE_BOX.left + SCORE_BOX.width, 0, 500, 100)

DRAW_SPRITES = True


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
        # stores the game sprites
        self.spritesheet = None
        # message sprite overlays
        self.messages = []
        # moonbase sprites (crete, radars, turrets)
        self.moonbase_sprites = {}
        # arcade sprites (asteroids, missiles, explosions)
        self.arcade_sprites = {}
        self.panels = collections.OrderedDict()
        self.windowsize = None
        # True while we are busy moving panels around
        self.transitioning = False
        # a pre-rendered image of the lunar surface
        self.moon_surface = None
        # list of colors to flash the background each tick
        self.flash_color = []
        # number counter sprites
        self.counters = []
        # track previous level score for resuming counters
        self.previous_score = 0
        # the sprite of time left to play the phase. set via controller.
        self.time_left = None
        # a counter for seconds passed while on the main menu.
        self.menu_ticker = 0

    def notify(self, event):
        """
        Called by an event in the message queue.

        """

        if isinstance(event, TickEvent):
            self.render()
            self.clock.tick(FPS)

        elif isinstance(event, InitializeEvent):
            self.initialize()

        elif isinstance(event, ResetGameEvent):
            self.moonbase_sprites = {}
            self.arcade_sprites = {}

        elif isinstance(event, StateEvent):
            if event.state in (STATE_PHASE1, STATE_PHASE2):
                self.counters = []
                self.panels['score'].show()
                self.panels['puzzle'].show()
                self.panels['results'].hide()
                self.panels['messages'].show()
                arcade_panel = self.panels['arcade']
                arcade_panel.scale((300, 225))
                arcade_panel.show_position = (0, 375)
                arcade_panel.show()
            elif event.state in (STATE_PHASE3, STATE_REPRIEVE):
                self.panels['score'].hide()
                self.panels['puzzle'].hide()
                self.panels['messages'].hide()
                arcade_panel = self.panels['arcade']
                arcade_panel.scale(ARCADE_POS.size)
                arcade_panel.show_position = ARCADE_POS.topleft
                arcade_panel.show()
            elif event.state in (STATE_LEVELDONE, STATE_LOSE):
                self.panels['results'].show()
            elif event.state == STATE_HELP:
                # TODO show the help panel
                pass
            elif event.state == STATE_MENU:
                self.panels['arcade'].hide()
                self.panels['score'].hide()
                self.panels['puzzle'].hide()
                self.panels['results'].hide()
                self.panels['messages'].hide()

            # display game messages
            if event.state == STATE_PHASE1:
                self.create_message('mix mooncrete', color.lighter_green)
            elif event.state == STATE_PHASE2:
                self.create_message('construct base', color.lighter_blue)
            elif event.state == STATE_PHASE3:
                self.create_message('alert: asteroids incoming!', color.lighter_yellow)
            elif event.state == STATE_REPRIEVE:
                if self.model.isplaying:
                    self.create_message('reinforcements arrived!', color.gold)
            elif event.state == STATE_LOSE:
                self.create_message('moonbase destroyed!', color.lighter_red)
            elif event.state == STATE_LEVELDONE:
                self.create_message('level win', color.gold)
            elif event.state == STATE_MENU:
                self.messages = []

        elif isinstance(event, LunarLandscapeClearedEvent):
            self.clear_lunar_landscape()

        elif isinstance(event, LunarLandSpawnEvent):
            self.prerender_lunar_landscape(event.land)

        elif isinstance(event, MooncreteSpawnEvent):
            self.create_mooncrete_sprite(event.mooncrete)

        elif isinstance(event, MooncreteDestroyEvent):
            self.destroy_mooncrete_sprite(event.mooncrete)
            self.panels['arcade'].shake(5)

        elif isinstance(event, BuildingSpawnEvent):
            self.create_building_sprite(event.building)

        elif isinstance(event, BuildingDestroyEvent):
            self.destroy_building_sprite(event.building)
            self.panels['arcade'].shake(5)

        elif isinstance(event, TurretSpawnedEvent):
            self.create_turret_sprite(event.turret)

        elif isinstance(event, TurretDestroyEvent):
            self.destroy_turret_sprite(event.turret)
            self.flash_screen([color.gold, color.black], 2)
            self.panels['arcade'].shake(15)

        elif isinstance(event, RadarSpawnedEvent):
            self.create_radar_sprite(event.radar)

        elif isinstance(event, RadarDestroyEvent):
            self.destroy_radar_sprite(event.radar)
            self.flash_screen([color.copper, color.black], 2)
            self.panels['arcade'].shake(5)

        elif isinstance(event, AsteroidSpawnedEvent):
            self.create_asteroid_sprite(event.asteroid)

        elif isinstance(event, AsteroidMovedEvent):
            self.move_asteroid(event.asteroid)

        elif isinstance(event, AsteroidDestroyEvent):
            self.destroy_asteroid(event.asteroid)
            self.flash_screen(color.dark_gray, 1)

        elif isinstance(event, MissileSpawnedEvent):
            self.create_missile(event.missile)

        elif isinstance(event, MissileMovedEvent):
            self.move_missile(event.missile)

        elif isinstance(event, MissileDestroyEvent):
            self.destroy_missile(event.missile)

        elif isinstance(event, ExplosionSpawnEvent):
            self.create_explosion(event.explosion)
            self.flash_screen(color.darker_gray, 1)

        elif isinstance(event, ExplosionGrowEvent):
            self.move_explosion(event.explosion)

        elif isinstance(event, ExplosionDestroyEvent):
            self.destroy_explosion(event.explosion)

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

        ## load music
        #pygame.mixer.music.load(data.filepath('moon-defense.xm'))
        #pygame.mixer.music.play(-1)

        # TODO custom cursor
        pygame.mouse.set_visible(True)
        # switch the target resolution based on fullscreen mode
        target_size = DRAW_AREA.size
        flags = 0
        if self.fullscreen:
            # use native monitor resolution
            #target_size = (0, 0)
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
        self.smallfont = pygame.font.Font(
            data.filepath('BLADRMF_.TTF'), 20)
        self.bigfont = pygame.font.Font(
            data.filepath('BLADRMF_.TTF'), 42)
        self.spritesheet = pygame.image.load(data.filepath('sprites.png')).convert()

        # load a random title screen image
        background_filename = 'title-screen-%s.png' % random.randint(1, 4)
        self.background = pygame.image.load(data.filepath(background_filename)).convert()

        # create floating game panels
        self.create_panels()

        # we are done
        self.isinitialized = True

    def flash_screen(self, color_list, duration):
        """
        Queue colors to flash the background with.

        """

        if type(color_list) is tuple:
            color_list = [color_list,]
        self.flash_color.extend(color_list * duration)

    def create_panels(self):
        """
        Build game panels that move around and show at various model states.

        """

        score_panel = Panel(SCORE_BOX.size, DRAW_AREA)
        score_panel.background_image = pygame.image.load(data.load('puzzle_info_bg.png')).convert()
        score_panel.border_image = pygame.image.load(data.load('puzzle_info.png')).convert()
        score_panel.border_image.set_colorkey(color.magenta)
        score_panel.show_position = SCORE_BOX.topleft
        score_panel.hide_position = (- SCORE_BOX.width, 0)
        score_panel.hide(instant=True)
        self.panels['score'] = score_panel

        puzzle_panel = Panel(PUZZLE_POS.size, DRAW_AREA)
        puzzle_panel.background_image = pygame.image.load(data.load('puzzle_bg.png')).convert()
        puzzle_panel.border_image = pygame.image.load(data.load('puzzle.png')).convert()
        puzzle_panel.border_image.set_colorkey(color.magenta)
        puzzle_panel.show_position = PUZZLE_POS.topleft
        puzzle_panel.hide_position = DRAW_AREA.bottomright
        puzzle_panel.hide(instant=True)
        self.panels['puzzle'] = puzzle_panel

        arcade_panel = Panel(ARCADE_POS.size, DRAW_AREA)
        arcade_panel.background_image = pygame.image.load(data.load('arcade_bg.png')).convert()
        arcade_panel.border_image = pygame.image.load(data.load('arcade.png')).convert()
        arcade_panel.border_image.set_colorkey(color.magenta)
        earth = pygame.image.load(data.load('earth.png')).convert()
        earth.set_colorkey(color.magenta)
        somewhere_over_the_rainbow = (random.randint(0, ARCADE_POS.width), random.randint(0, ARCADE_POS.height))
        arcade_panel.background_image.blit(earth, somewhere_over_the_rainbow)
        arcade_panel.hide_position = (0, ARCADE_POS.height)
        arcade_panel.hide(instant=True)
        self.panels['arcade'] = arcade_panel

        results_screen = pygame.image.load(data.load('results.png')).convert()
        results_panel = Panel(results_screen.get_size(), DRAW_AREA)
        results_panel.background_image = results_screen
        results_panel.show_position = (
            (DRAW_AREA.width - results_panel.rect.width) / 2,
            (DRAW_AREA.height - results_panel.rect.height) / 2)
        results_panel.hide_position = (DRAW_AREA.width, 0)
        results_panel.hide(instant=True)
        self.panels['results'] = results_panel

        msg_panel = Panel(MESSAGE_POS.size, DRAW_AREA)
        msg_panel.background_image = pygame.image.load(data.load('messages_bg.png')).convert()
        msg_panel.border_image = pygame.image.load(data.load('messages.png')).convert()
        msg_panel.border_image.set_colorkey(color.magenta)
        msg_panel.show_position = MESSAGE_POS.topleft
        msg_panel.hide_position = DRAW_AREA.topright
        msg_panel.hide(instant=True)
        self.panels['messages'] = msg_panel

    def load_sprites(self, target):
        """
        Loads sprite images into the target.

        """

        if type(target) is MooncreteSprite:
            rect = (7, 80, 33, 33)
            target.image = self.spritesheet.subsurface(rect)

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

        ticks = pygame.time.get_ticks()
        state = self.model.state
        if self.flash_color:
            self.image.fill(self.flash_color.pop())
        else:
            #self.image.fill((0, 0, 0))
            self.image.blit(self.background, (0, 0))

        if state == STATE_MENU:
            self.draw_menu()

        elif state == STATE_HELP:
            pass

        elif state in (STATE_LEVELDONE, STATE_LOSE):
            self.clear_arcade()
            self.draw_moonbase(ticks)
            self.draw_results(ticks)

        elif state in (STATE_PHASE1, STATE_PHASE2):
            self.draw_puzzle_blocks()
            self.clear_arcade()
            self.draw_moonbase(ticks)
            self.draw_scorebox()

        elif state in (STATE_PHASE3, STATE_LOSE, STATE_REPRIEVE):
            self.clear_arcade()
            self.draw_moonbase(ticks)
            self.angle_turrets()
            self.draw_missiles_and_asteroids(ticks)
            self.draw_firing_solution()

        # render game panels
        self.transitioning = False
        for key, panel in self.panels.items():
            if panel.draw(self.image):
                self.transitioning = True

        # render game messages
        if self.messages:
            message_sprite = self.messages[0]
            message_sprite.update(ticks)
            # puzzle phases draw messages to a dedicated panel.
            # otherwise they overlay on the main screen.
            if state in (STATE_PHASE1, STATE_PHASE2):
                self.panels['messages'].clear()
                message_sprite.draw(self.panels['messages'].image)
            else:
                message_sprite.draw(self.image)
            if message_sprite.expired:
                self.messages.remove(message_sprite)

        self.screen.blit(self.image, DRAW_AREA)
        pygame.display.flip()

    def create_message(self, message, forecolor):
        """
        Create a message overlay.

        """

        # the current phase determines color and movement
        timeout = 5
        if self.model.state in (STATE_PHASE1, STATE_PHASE2):
            origin = (MESSAGE_POS.width / 2, 0)
            destination = (origin[0], (MESSAGE_POS.height - 60) / 2)
        else:
            origin = (ARCADE_POS.width / 2, 0)
            destination = (origin[0], MESSAGE_POS.height / 2)
        sprite = MessageSprite(
            message=message,
            font=self.bigfont,
            timeout=timeout,
            forecolor=forecolor,
            backcolor=color.magenta,
            draw_border=False)
        # center the destination with the sprite image size
        sprite.rect.center = origin
        sprite.destination = sprite.image.get_rect(midtop=destination).topleft
        #self.messages.append(sprite)
        self.messages = [sprite]

    def set_time_left(self, seconds):
        """
        Set the time left to play the phase.

        """

        minutes = seconds / 60
        seconds = seconds % 60
        if (self.model.state == STATE_PHASE3):
            left_text = 'reinforcements in %02d:%02d' % (minutes, seconds)
        else:
            left_text = 'time left: %02d:%02d' % (minutes, seconds)
        self.time_left = self.smallfont.render(
            left_text, False,
            color.white)

    def draw_scorebox(self):
        """
        Draw the score box for phases I & II.

        """

        score_panel = self.panels['score']
        score_panel.clear()
        if self.time_left:
            score_panel.image.blit(self.time_left, (10, 60))

    def draw_results(self, ticks):
        """
        Draw the game results panel.

        """

        # draw the title "Level n complete" / "fail"
        # draw "Asteroids destroyed"
        # draw an animating score adder upper next to that.
        # draw "Moon bases built"
        # draw an animating score adder upper next to that.
        # draw an animating score adder upper for total score.

        panel = self.panels['results']
        panel.clear()
        image = panel.image

        if self.model.state == STATE_LEVELDONE:
            pix = self.smallfont.render(
                'level %s - base survived' % (self.model.level),
                False, color.white)
            image.blit(pix, (25, 15))

        elif self.model.state == STATE_LOSE:
            pix = self.smallfont.render(
                'level %s - base destroyed' % (self.model.level),
                False, color.lighter_red)
            image.blit(pix, (25, 15))

        pix = self.smallfont.render(
            '%s asteroids stopped' % (self.model.asteroids_destroyed),
            False, color.lighter_blue)
        image.blit(pix, (25, 55))

        pix = self.smallfont.render(
            '%s bases built' % (self.model.moonbases_built),
            False, color.lighter_blue)
        image.blit(pix, (25, 85))

        pix = self.smallfont.render(
            '%s bases destroyed' % (self.model.moonbases_destroyed),
            False, color.lighter_red)
        image.blit(pix, (25, 115))

        pix = self.bigfont.render('score', False, color.white)
        image.blit(pix, (25, 230))

        if self.model.state == STATE_LOSE:
            pix = self.bigfont.render('game over', False, color.lighter_red)
            image.blit(pix, (25, 180))

        # add bonus counters
        if not self.counters:
            self.counters.append(
                NumberCounterSprite(
                    pygame.Rect((330, 55), ARCADE_SPRITE_SIZE),
                    0, self.model.bonus_asteroids,
                    self.smallfont, color.lighter_blue))
            self.counters.append(
                NumberCounterSprite(
                    pygame.Rect((330, 85), ARCADE_SPRITE_SIZE),
                    0, self.model.bonus_base,
                    self.smallfont, color.lighter_blue))
            self.counters.append(
                NumberCounterSprite(
                    pygame.Rect((330, 115), ARCADE_SPRITE_SIZE),
                    0, self.model.bonus_base_destroyed,
                    self.smallfont, color.lighter_red))
            self.counters.append(
                NumberCounterSprite(
                    pygame.Rect((330, 230), ARCADE_SPRITE_SIZE),
                    self.previous_score, self.model.score,
                    self.bigfont, color.white))
            self.previous_score = self.model.score

        for counter in self.counters:
            counter.update(ticks)
            counter.draw(self.panels['results'].image)

    def convert_puzzle_to_panel(self, position):
        """
        Convert a puzzle model position into a view pixel value.

        """

        return (int(float(position[0]) / model.PUZZLE_WIDTH * PUZZLE_POS.width),
                int(float(position[1]) / model.PUZZLE_HEIGHT * PUZZLE_POS.height))

    def convert_arcade_to_panel(self, position):
        """
        Convert an arcade model position into a view pixel value.

        """

        return (int(float(position[0]) / model.ARCADE_WIDTH * ARCADE_POS.width),
                int(float(position[1]) / model.ARCADE_HEIGHT * ARCADE_POS.height))

    def convert_screen_to_arcade(self, position):
        """
        Take a screen position and translate to an arcade equivalent.

        """

        x = (model.ARCADE_WIDTH / float(DRAW_AREA.width)) * position[0]
        y = (model.ARCADE_HEIGHT / float(DRAW_AREA.height)) * position[1]
        return (int(x), int(y))

    def convert_arcade_to_screen(self, position):
        """
        Take an arcade position and translate to a screen equivalent.

        """

        x = (DRAW_AREA.width / float(model.ARCADE_WIDTH)) * position[0]
        y = (DRAW_AREA.height / float(model.ARCADE_HEIGHT)) * position[1]
        return (int(x), int(y))

    def menu_ticker_step(self):
        """
        Called to step the menu ticker counter.

        """

        self.menu_ticker = (self.menu_ticker + 1) % 30

    def draw_menu(self):
        """
        Draw the menu screen.

        """

        # draw the game title
        pix = self.bigfont.render('mooncrete', False, color.white)
        self.image.blit(pix, (20, 20))

        # draw high scores after n seconds
        score_delay = 4
        if self.menu_ticker >= score_delay:
            pix = self.bigfont.render('scores', False, color.lighter_green)
            self.image.blit(pix, (20, 100))
            scores = (
                ('flarty', 'Jan 2013', 1000),
                ('snafu', 'Feb 2013', 900),
                ('nurgle', 'Mar 2013', 800),
                ('spamley', 'Apr 2013', 700),
                )
            score_y = 160
            for position, (name, date, score) in enumerate(scores):
                if position < self.menu_ticker - score_delay:
                    position_str = '#%s --' % (position + 1)
                    score_str = (' %s points ' % (score,)).ljust(20, '-')
                    name_str = (' %s ' % (name,)).ljust(20, '-')
                    pix = self.smallfont.render(
                        '%s%s%s %s' % (position_str, score_str, name_str, date),
                        False,
                        color.lighter_green
                        )
                    self.image.blit(pix, (20, score_y))
                    score_y += pix.get_height()

        # tell the player how to start
        if self.model.isplaying:
            start_message = 'spacebar continues your game...'
        else:
            start_message = 'spacebar begins a new game'
        pix = self.smallfont.render(start_message, False, color.lighter_yellow)
        self.image.blit(pix, (20, DRAW_AREA.height - 30))

    def draw_puzzle_blocks(self):
        pan = self.panels['puzzle']
        pan.clear()
        for x, y, v in self.model.puzzle_board_data():
            if v:
                position = pygame.Rect(
                    self.convert_puzzle_to_panel((x, y)),
                    PUZZLE_BLOCK_SIZE
                    )
                sprite_loc = None
                block_color = (128, 128, 128)

                if v == model.BLOCK_EMPTY_BARREL:
                    block_color = (32, 32, 32)
                    sprite_loc = pygame.Rect(33, 99, 33, 33)

                elif v == model.BLOCK_MOONROCKS:
                    block_color = (32, 32, 32)
                    sprite_loc = pygame.Rect(33, 66, 33, 33)

                elif v == model.BLOCK_CALCIUM_BARREL:
                    block_color = (0, 128, 0)
                    sprite_loc = pygame.Rect(33, 132, 33, 33)

                elif v == model.BLOCK_WATER_BARREL:
                    block_color = (0, 64, 0)
                    sprite_loc = pygame.Rect(33, 165, 33, 33)

                elif v == model.BLOCK_RADAR_BITS:
                    block_color = (128, 0, 0)
                    sprite_loc = pygame.Rect(33, 198, 33, 33)

                elif v == model.BLOCK_RADAR_DISH:
                    block_color = (64, 0, 0)
                    sprite_loc = pygame.Rect(33, 231, 33, 33)

                elif v == model.BLOCK_TURRET_AMMO:
                    block_color = (0, 0, 128)
                    sprite_loc = pygame.Rect(33, 297, 33, 33)

                elif v == model.BLOCK_TURRET_BASE:
                    block_color = (0, 0, 64)
                    sprite_loc = pygame.Rect(33, 264, 33, 33)

                if DRAW_SPRITES and sprite_loc:
                    pan.image.blit(
                        self.spritesheet.subsurface(sprite_loc),
                        position)
                else:
                    pygame.draw.rect(pan.image, block_color, position)

    def placeholder_pix(self, size, acolor):
        pix = pygame.Surface(size)
        pix.set_colorkey(color.magenta)
        pix.fill(acolor)
        return pix

    def clear_lunar_landscape(self):
        """
        Clear the lunar landscape surface.

        """

        self.moon_surface = pygame.Surface(ARCADE_POS.size)
        self.moon_surface.set_colorkey(color.magenta)
        self.moon_surface.fill(color.magenta)

    def prerender_lunar_landscape(self, land):
        """
        Draw the given land (a lunar land) onto a surface.

        """

        position = self.convert_arcade_to_panel(land.position)
        rect = pygame.Rect(position, ARCADE_SPRITE_SIZE)
        pygame.draw.rect(self.moon_surface, color.darker_gray, rect)

    def clear_arcade(self):
        """
        Clears the arcade image.

        """

        self.panels['arcade'].clear()

    def draw_missiles_and_asteroids(self, ticks):
        """
        Draw missile and asteroid sprites.

        """

        for key, sprite in self.arcade_sprites.items():
            sprite.update(ticks)
            if sprite.image:
                self.panels['arcade'].image.blit(sprite.image, sprite.rect)

    def draw_moonbase(self, ticks):
        """
        Draw the moon base sprites and the lunar land scape.

        """

        arcade_image = self.panels['arcade'].image

        for key, sprite in self.moonbase_sprites.items():
            sprite.update(ticks)
            arcade_image.blit(sprite.image, sprite.rect)

        # draw the pre-rendered moon surface
        if self.moon_surface:
            arcade_image.blit(self.moon_surface, (0, 0))

        if (self.model.state == STATE_PHASE3):
            if self.time_left:
                arcade_image.blit(self.time_left,
                    (10, ARCADE_POS.height - self.time_left.get_height() - 5))


    def draw_firing_solution(self):
        """
        Draws a firing solution from the closest ready turret to the cursor.

        """

        mouse_pos = pygame.mouse.get_pos()
        arcade_pos = self.convert_screen_to_arcade(mouse_pos)
        turret = self.model.closest_ready_turret(arcade_pos)
        if turret:
            turret_pos = self.convert_arcade_to_screen(turret.position)
            # center the origin x
            turret_pos = (turret_pos[0] + ARCADE_SPRITE_SIZE[0] / 2, turret_pos[1])
            image = self.panels['arcade'].image
            pygame.draw.line(image, color.darkest_green, mouse_pos, turret_pos)

    def angle_turrets(self):
        """
        Angle turrets towards the cursor.

        """

        for key, sprite in self.moonbase_sprites.items():
            if isinstance(sprite, TurretSprite):
                angle = helper.angle(
                    sprite.rect.center,
                    pygame.mouse.get_pos()
                    )
                sprite.turrent_angle_override = angle

    def moonbase_sprite_origin(self):
        """
        Gives a rect for moon base sprite origin when building your base.

        """

        return pygame.Rect((ARCADE_POS.width / 2, 0), ARCADE_SPRITE_SIZE)

    def create_mooncrete_sprite(self, mooncrete):
        """
        Create a mooncrete sprite.

        """

        destination = pygame.Rect(
            self.convert_arcade_to_panel(mooncrete.position),
            ARCADE_SPRITE_SIZE)
        sprite = MooncreteSprite(self.moonbase_sprite_origin())
        sprite.destination = destination
        sprite.image = self.placeholder_pix(ARCADE_SPRITE_SIZE, color.dark_gray)
        self.moonbase_sprites[mooncrete.id] = sprite

    def destroy_mooncrete_sprite(self, mooncrete):
        """
        Destroy a mooncrete sprite.

        """

        if self.moonbase_sprites.has_key(mooncrete.id):
            del self.moonbase_sprites[mooncrete.id]

    def create_building_sprite(self, building):
        """
        Create a moon base building.

        """

        destination = pygame.Rect(
            self.convert_arcade_to_panel(building.position),
            ARCADE_SPRITE_SIZE)
        sprite = MoonbaseSprite()
        sprite.rect = self.moonbase_sprite_origin()
        sprite.destination = destination
        sprite.image = self.placeholder_pix(ARCADE_SPRITE_SIZE, color.light_gray)
        self.moonbase_sprites[building.id] = sprite

    def destroy_building_sprite(self, building):
        """
        Destroy a moon base building sprite.

        """

        if self.moonbase_sprites.has_key(building.id):
            del self.moonbase_sprites[building.id]

    def create_turret_sprite(self, turret):
        """
        Create a turret sprite.

        """

        destination = pygame.Rect(
            self.convert_arcade_to_panel(turret.position),
            ARCADE_SPRITE_SIZE)
        sprite = TurretSprite(self.moonbase_sprite_origin())
        sprite.turret = turret
        sprite.destination = destination
        sprite.image = self.placeholder_pix(ARCADE_SPRITE_SIZE, color.gold)
        self.moonbase_sprites[turret.id] = sprite

    def destroy_turret_sprite(self, turret):
        """
        Destroy a turret sprite.

        """

        if self.moonbase_sprites.has_key(turret.id):
            del self.moonbase_sprites[turret.id]

    def create_radar_sprite(self, radar):
        """
        Create a radar sprite.

        """

        destination = pygame.Rect(
            self.convert_arcade_to_panel(radar.position),
            ARCADE_SPRITE_SIZE)
        sprite = MoonbaseSprite()
        sprite.rect = self.moonbase_sprite_origin()
        sprite.destination = destination
        sprite.image = self.placeholder_pix(ARCADE_SPRITE_SIZE, color.copper)
        self.moonbase_sprites[radar.id] = sprite

    def destroy_radar_sprite(self, radar):
        """
        Destroy a radar sprite.

        """

        if self.moonbase_sprites.has_key(radar.id):
            del self.moonbase_sprites[radar.id]

    def create_asteroid_sprite(self, asteroid):
        """
        Create an asteroid sprite from the given model asteroid object.

        """

        position = self.convert_arcade_to_panel(asteroid.position)
        rect = pygame.Rect(position, ARCADE_SPRITE_SIZE)
        sprite = AsteroidSprite()
        sprite.rect = rect
        sprite.image = self.placeholder_pix(ARCADE_SPRITE_SIZE, color.magenta)
        pygame.draw.circle(
            sprite.image,
            color.white,
            (ARCADE_SPRITE_SIZE[0] / 2, ARCADE_SPRITE_SIZE[1] / 2),
            ARCADE_SPRITE_SIZE[0] / 3)
        self.arcade_sprites[asteroid.id] = sprite

    def move_asteroid(self, asteroid):
        """
        Move the given model asteroid sprite.

        """

        sprite = self.arcade_sprites.get(asteroid.id, None)
        if sprite:
        # convert indexes to screen coordinates
            position = self.convert_arcade_to_panel(asteroid.position)
            sprite.rect.center = position

    def destroy_asteroid(self, asteroid):
        """
        Destroy the given asteroid sprite.

        """

        if self.arcade_sprites.has_key(asteroid.id):
            del self.arcade_sprites[asteroid.id]
        # TODO spawn an asteroid destroy animation

    def create_missile(self, missile):
        """
        Create a sprite for a missile.

        Missiles are drawn with their centers at the point of contact.
        The angle between their starting position and destination is
        used to rotate their image.

        """

        start_rect = pygame.Rect((0, 0), ARCADE_SPRITE_SIZE)
        start_rect.center = self.convert_arcade_to_screen(missile.position)
        end_rect = pygame.Rect((0, 0), ARCADE_SPRITE_SIZE)
        end_rect.center = self.convert_arcade_to_screen(missile.destination)

        # use a placehold image
        pix = self.placeholder_pix(ARCADE_SPRITE_SIZE, color.magenta)
        pygame.draw.line(
            pix, color.white, (0, start_rect.height / 2),
            (start_rect.width, start_rect.height / 2), 2)

        # rotate the image by the angle
        angle = helper.angle(start_rect.center, end_rect.center)
        pix = pygame.transform.rotate(pix, angle)
        sprite = MissileSprite(start_rect, pix)
        self.arcade_sprites[missile.id] = sprite
        # set initial position
        self.move_missile(missile)

    def move_missile(self, missile):
        """
        Move a missile.

        """

        sprite = self.arcade_sprites.get(missile.id, None)
        if sprite:
            position = self.convert_arcade_to_screen(missile.position)
            sprite.rect.center = position

    def destroy_missile(self, missile):
        """
        Destroy a missile.

        """

        if self.arcade_sprites.has_key(missile.id):
            del self.arcade_sprites[missile.id]

    def create_explosion(self, explosion):
        """
        Create an explosion sprite.

        """

        position = self.convert_arcade_to_screen(explosion.position)
        sprite = ExplosionSprite(position)
        self.arcade_sprites[explosion.id] = sprite

    def move_explosion(self, explosion):
        """
        Grow an explosion sprite.

        """

        sprite = self.arcade_sprites.get(explosion.id, None)
        if sprite:
            sprite.grow(explosion.radius * 10)

    def destroy_explosion(self, explosion):
        """
        Destroy an explosion sprite.

        """

        if self.arcade_sprites.has_key(explosion.id):
            del self.arcade_sprites[explosion.id]
