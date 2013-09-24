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
    PUZZLE_POS.height / model.PUZZLE_WIDTH)

# arcade position and size (takes full draw area)
ARCADE_POS = DRAW_AREA.copy()

# The size of an arcade sprite is in ratio to the arcade view size
# to the model arcade size.
ARCADE_SPRITE_SIZE = (
    ARCADE_POS.width // (model.ARCADE_WIDTH / model.BLOCK_PADDING),
    ARCADE_POS.height // (model.ARCADE_HEIGHT / model.BLOCK_PADDING))


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
        # message sprite overlays
        self.messages = []
        # moonbase sprites (crete, radars, turrets)
        self.moonbase_sprites = {}
        # arcade sprites (asteroids, missiles, explosions)
        self.arcade_sprites = {}
        self.panels = {}
        self.windowsize = None
        # True while we are busy moving panels around
        self.transitioning = False
        # a pre-rendered image of the lunar surface
        self.moon_surface = None
        # list of colors to flash the background each tick
        self.flash_color = []

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
                self.panels['score'].show()
                self.panels['puzzle'].show()
                arcade_panel = self.panels['arcade']
                arcade_panel.scale((300, 225))
                arcade_panel.show_position = (0, 375)
                arcade_panel.show()
            elif event.state in (STATE_PHASE3, STATE_LOSE, STATE_REPRIEVE):
                self.panels['score'].hide()
                self.panels['puzzle'].hide()
                arcade_panel = self.panels['arcade']
                arcade_panel.scale(ARCADE_POS.size)
                arcade_panel.show_position = ARCADE_POS.topleft
                arcade_panel.show()
            elif event.state == STATE_HELP:
                # TODO show the help panel
                pass
            elif event.state == STATE_MENU:
                self.panels['arcade'].hide()
                self.panels['score'].hide()
                self.panels['puzzle'].hide()

            # display game messages
            if event.state == STATE_PHASE1:
                self.create_message('Build Foundation', color.gold)
            elif event.state == STATE_PHASE2:
                self.create_message('Construct Moonbase', color.gold)
            elif event.state == STATE_PHASE3:
                self.create_message('Asteroids Incoming!', color.gold)
            elif event.state == STATE_REPRIEVE:
                self.create_message('Wave Complete', color.gold)
            elif event.state == STATE_LOSE:
                self.create_message('Moonbase Destroyed', color.gold)
            elif event.state == STATE_LEVELDONE:
                self.create_message('Level Complete', color.gold)

        elif isinstance(event, LunarLandscapeClearedEvent):
            self.clear_lunar_landscape()

        elif isinstance(event, LunarLandSpawnEvent):
            self.prerender_lunar_landscape(event.land)

        elif isinstance(event, MooncreteSpawnEvent):
            self.create_mooncrete_sprite(event.mooncrete)

        elif isinstance(event, MooncreteDestroyEvent):
            self.destroy_mooncrete_sprite(event.mooncrete)

        elif isinstance(event, TurretSpawnedEvent):
            self.create_turret_sprite(event.turret)

        elif isinstance(event, TurretDestroyEvent):
            self.destroy_turret_sprite(event.turret)
            self.flash_screen([color.gold, color.black], 2)

        elif isinstance(event, RadarSpawnedEvent):
            self.create_radar_sprite(event.radar)

        elif isinstance(event, RadarDestroyEvent):
            self.destroy_radar_sprite(event.radar)
            self.flash_screen([color.copper, color.black], 2)

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
        self.bigfont = pygame.font.Font(
            os.path.join('..','data','Vermin Vibes 2 Black.otf'), 42)

        #self.background = image.load('background.png').convert()

        self.create_panels()

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
        # the score panel is visible at the top-left of the screen
        score_panel.show_position = SCORE_BOX.topleft
        # and it hides to the left
        score_panel.hide_position = (- SCORE_BOX.width, 0)
        score_panel.hide(instant=True)
        self.panels['score'] = score_panel

        puzzle_panel = Panel(PUZZLE_POS.size, DRAW_AREA)
        # puzle grid is visible at the top-left of the screen
        puzzle_panel.show_position = PUZZLE_POS.topleft
        # and it hides to the right, off-screen
        puzzle_panel.hide_position = (DRAW_AREA.width, 0)
        puzzle_panel.hide(instant=True)
        self.panels['puzzle'] = puzzle_panel

        arcade_panel = Panel(ARCADE_POS.size, DRAW_AREA)
        arcade_panel.hide_position = (0, ARCADE_POS.height)
        arcade_panel.hide(instant=True)
        self.panels['arcade'] = arcade_panel

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
            self.image.fill((0, 0, 0))

        if state == STATE_MENU:
            pass

        elif state == STATE_HELP:
            pix = self.smallfont.render(
                'help screen for phase %s' % (self.model._last_phase),
                False, color.white, color.magenta)
            pix.set_colorkey(color.magenta)
            self.panels['score'].image.blit(pix, (0, 0))
            pass

        elif state == STATE_LEVELDONE:
            pass

        elif state in (STATE_PHASE1, STATE_PHASE2):
            self.draw_puzzle_blocks()
            self.clear_arcade()
            self.draw_moonbase(ticks)

        elif state in (STATE_PHASE3, STATE_LOSE, STATE_REPRIEVE):
            self.angle_turrets()
            self.clear_arcade()
            self.draw_moonbase(ticks)
            self.draw_missiles_and_asteroids(ticks)
            self.draw_firing_solution()

            if (state == STATE_LOSE):
                pix = self.smallfont.render(
                    'You Lose!',
                    False, color.white, color.magenta)
                pix.set_colorkey(color.magenta)
                self.panels['arcade'].image.blit(pix, (300, 250))

        # update panels
        self.transitioning = False
        for key, panel in self.panels.items():
            if panel.draw(self.image):
                self.transitioning = True

        # update messages
        for message_sprite in self.messages:
            message_sprite.update(ticks)
            message_sprite.draw(self.image)
            if message_sprite.expired:
                self.messages.remove(message_sprite)
                break

        pix = self.smallfont.render(
            'Mooncrete -- press space to play',
            False, color.white, color.magenta)
        pix.set_colorkey(color.magenta)
        self.image.blit(pix, (15, 15))
        self.screen.blit(self.image, DRAW_AREA)
        pygame.display.flip()

    def create_message(self, message, forecolor):
        """
        Create a message overlay.

        """

        # the current phase determines color and movement
        timeout = 5
        origin = (0, ARCADE_POS.height / 2)
        destination = (ARCADE_POS.width / 2, ARCADE_POS.height / 2)
        sprite = MessageSprite(
            message=message,
            font=self.bigfont,
            timeout=timeout,
            forecolor=forecolor)
        sprite.rect.center = origin
        # center the destination with the sprite image size
        sprite.destination = sprite.image.get_rect(center=destination).topleft
        self.messages.append(sprite)

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

    def convert_puzzle_to_screen(self, position):
        pos = self.convert_puzzle_to_panel(position)
        return self.panels['puzzle'].point_to_screen(pos)

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

    def draw_puzzle_blocks(self):
        pan = self.panels['puzzle']
        pan.image.fill(color.darker_gray)
        for x, y, v in self.model.puzzle_board_data():
            if v:
                rect = pygame.Rect(
                    self.convert_puzzle_to_panel((x, y)),
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

        self.panels['arcade'].image.fill(color.magenta)

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

        for key, sprite in self.moonbase_sprites.items():
            sprite.update(ticks)
            self.panels['arcade'].image.blit(sprite.image, sprite.rect)

        # draw the pre-rendered moon surface
        if self.moon_surface:
            self.panels['arcade'].image.blit(self.moon_surface, (0, 0))

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
            pygame.draw.line(self.image, color.darkest_green, mouse_pos, turret_pos)

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

        del self.arcade_sprites[asteroid.id]
        # TODO spawn an asteroid destroy animation

    def create_missile(self, missile):
        """
        Create a sprite for a missile.

        """

        # the missile position and destination is the arcade coordinate target.
        position = self.convert_arcade_to_screen(missile.position)
        rect = pygame.Rect(position, ARCADE_SPRITE_SIZE)
        # destination used by the sprite to calc it's angle of rotation
        dest_coords = self.convert_arcade_to_screen(missile.destination)
        destination = pygame.Rect((0, 0), ARCADE_SPRITE_SIZE)
        destination.center = dest_coords
        # use a placehold image
        pix = self.placeholder_pix(ARCADE_SPRITE_SIZE, color.magenta)
        sprite = MissileSprite(rect, pix, destination)
        sprite.missile = missile
        self.arcade_sprites[missile.id] = sprite

    def move_missile(self, missile):
        """
        Move a missile.

        """

        sprite = self.arcade_sprites.get(missile.id, None)
        if sprite:
            position = self.convert_arcade_to_screen(missile.position)
            sprite.rect.topleft = position

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
