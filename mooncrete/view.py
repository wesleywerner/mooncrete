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

# The region where puzzle gameplay happens.
# It is achored to the top-right of the screen.
# It hides to the right off-screen.
PUZZLE_AREA = pygame.Rect(0, 0, 500, 500)
PUZZLE_AREA.topleft = (DRAW_AREA.width - PUZZLE_AREA.width, 0)

# The region where arcade gameplay happens
#ARCADE_AREA = DRAW_AREA.copy()

# The mini moonscape lives below the puzzle area.
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
# This size is strictly used to MAP the screen to the mini moonscape.
# Used when block float down to the mini view, it uses these to know
# where to float to, so the sprite matches up to the final panel position.
MOONSCAPE_MINI_SIZE = (MOONSCAPE_MINI.width // model.MOONSCAPE_WIDTH,
                        MOONSCAPE_MINI.height // model.MOONSCAPE_HEIGHT)

ARCADE_VIEW_MODEL_RATIO = (DRAW_AREA.width // model.ARCADE_WIDTH,
                            DRAW_AREA.height // model.ARCADE_HEIGHT)

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
        # moonbase sprites that get drawn onto the moonscape panel
        self.moonbase_sprites = {}
        # courier sprites between panels with a flying sprite
        self._courier_sprites = {}
        # all arcade sprites (asteroids, missiles...)
        self.arcade_sprites = {}
        self.panels = {}
        self.windowsize = None
        # True while we are busy moving panels around
        self.transitioning = False
        # a pre-rendered image of the game moonscape surface
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

        elif isinstance(event, StateEvent):
            if event.state in (STATE_PHASE1, STATE_PHASE2):
                self.panels['arcade'].hide()
                self.panels['score'].show()
                self.panels['puzzle'].show()
                moonscape = self.panels['moonscape']
                moonscape.show()
                moonscape.show_position = MOONSCAPE_MINI.topleft
                moonscape.scale(MOONSCAPE_MINI.size)
            elif event.state == STATE_PHASE3:
                self.panels['arcade'].show()
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
                self.panels['arcade'].hide()
                self.panels['score'].hide()
                self.panels['puzzle'].hide()
                self.panels['moonscape'].hide()

        elif isinstance(event, MoonscapeGeneratedEvent):
            self.prerender_moonscape()
            self.draw_moonscape()

        elif isinstance(event, MooncreteSpawnEvent):
            self.create_mooncrete_sprite(event.mooncrete, event.flyin_position)

        elif isinstance(event, MooncreteDestroyEvent):
            self.destroy_mooncrete_sprite(event.mooncrete)

        elif isinstance(event, TurretSpawnedEvent):
            self.create_turret_sprite(event.turret, event.flyin_position)

        elif isinstance(event, TurretDestroyEvent):
            self.destroy_turret_sprite(event.turret)
            self.flash_screen(color.red, 4)

        elif isinstance(event, RadarSpawnedEvent):
            self.create_radar_sprite(event.radar, event.flyin_position)

        elif isinstance(event, RadarDestroyEvent):
            self.destroy_radar_sprite(event.radar)
            self.flash_screen([color.red, color.white], 2)

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
        moonscape_panel.hide_position = (MOONSCAPE_MINI.left, DRAW_AREA.height)
        moonscape_panel.hide(instant=True)
        self.panels['moonscape'] = moonscape_panel

        arcade_panel = Panel(DRAW_AREA.size, DRAW_AREA)
        arcade_panel.show_position = DRAW_AREA.topleft
        arcade_panel.hide_position = (DRAW_AREA.left, - DRAW_AREA.height)
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

        state = self.model.state
        if self.flash_color:
            self.image.fill(self.flash_color.pop())
        else:
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
            self.draw_moonscape()

        elif state == STATE_PHASE3:
            self.draw_arcade_sprites()
            self.draw_moonscape()

        # update panels
        self.transitioning = False
        for key, panel in self.panels.items():
            if panel.draw(self.image):
                self.transitioning = True

        # moving moonbases are draw on top of all other panels
        self.courier_deliver_sprite()

        pix = self.smallfont.render(
            'Mooncrete -- press space to play',
            False, color.white, color.magenta)
        pix.set_colorkey(color.magenta)
        self.image.blit(pix, (15, 15))
        self.screen.blit(self.image, DRAW_AREA)
        pygame.display.flip()

    def convert_puzzle_to_panel(self, position):
        return (position[0] * PUZZLE_BLOCK_SIZE[0],
                position[1] * PUZZLE_BLOCK_SIZE[1])

    def convert_mini_moonscape_to_panel(self, position):
        return (position[0] * MOONSCAPE_MINI_SIZE[0],
                position[1] * MOONSCAPE_MINI_SIZE[1])

    def convert_moonscape_to_panel(self, position):
        return (position[0] * MOONSCAPE_BLOCK_SIZE[0],
                position[1] * MOONSCAPE_BLOCK_SIZE[1])

    def translate_to_screen(self, position, container_position):
        return (position[0] + container_position[0],
                position[1] + container_position[1])

    def convert_puzzle_to_screen(self, position):
        pos = self.convert_puzzle_to_panel(position)
        pos = self.translate_to_screen(
            pos, self.panels['puzzle'].rect.topleft)
        return pos

    def convert_moonscape_to_screen(self, position):
        pos = self.convert_moonscape_to_panel(position)
        pos = self.translate_to_screen(
            pos, self.panels['moonscape'].rect.topleft)
        return pos

    def convert_mini_moonscape_to_screen(self, position):
        pos = self.convert_mini_moonscape_to_panel(position)
        pos = self.translate_to_screen(
            pos, self.panels['moonscape'].rect.topleft)
        return pos

    def convert_screen_to_arcade(self, position):
        """
        Take a screen position and translate to an arcade equivalent.

        """

        x = (model.ARCADE_WIDTH / float(DRAW_AREA.width)) * position[0]
        y = (model.ARCADE_HEIGHT / float(DRAW_AREA.height)) * position[1]
        return (int(x), int(y))

    def convert_arcade_to_screen(self, position):
        """
        Take a arcade position and translate to a screen equivalent.

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
        pix.fill(acolor)
        return pix

    def courier_send_sprite(self, cargo_id, cargo, fly_from, fly_to):
        """
        courier a sprite from the puzzle area to the moonscape via
        a flying sprite. It carries the cargo and upon reaching its
        destination, drops the cargo in the moonbase sprite list.

        cargo_id is the key used storing dictionary entries.
        fly_from is puzzle grid coordinates.
        fly_to is moonscape grid coordinates.

        """

        from_coords = pygame.Rect(
            self.convert_puzzle_to_screen(fly_from), MOONSCAPE_BLOCK_SIZE)
        to_coords = self.convert_mini_moonscape_to_screen(fly_to)
        fly = CourierSprite(
            rect=from_coords,
            image=cargo.image,
            destination=to_coords,
            cargo=cargo
            )
        self._courier_sprites[cargo_id] = fly

    def courier_deliver_sprite(self):
        """
        Update courier sprites that deliver a cargo sprite to the moonscape.

        """

        t = pygame.time.get_ticks()
        retirement_list = []
        for key, courier in self._courier_sprites.items():
            courier.update(t)
            self.image.blit(courier.image, courier.rect)
            if courier.at_destination:
                self.moonbase_sprites[key] = courier.cargo
                retirement_list.append(key)
        for delivery in retirement_list:
            del self._courier_sprites[delivery]

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
        moonscape = self.panels['moonscape']
        moonscape.image.fill(color.magenta)

        # animate moon base sprites
        t = pygame.time.get_ticks()
        for key, sprite in self.moonbase_sprites.items():
            sprite.update(t)
            moonscape.image.blit(sprite.image, sprite.rect)

        # draw the pre-rendered moon surface
        if self.moon_surface:
            moonscape.image.blit(self.moon_surface, (0, 0))

    def draw_arcade_sprites(self):
        """
        Animate and draw flying asteroids.

        """

        pan = self.panels['arcade']
        pan.image.fill(color.magenta)
        t = pygame.time.get_ticks()
        for key, sprite in self.arcade_sprites.items():
            sprite.update(t)

            if sprite.image:
                pan.image.blit(sprite.image, sprite.rect)

            ## draw the missile firing solution
            #if isinstance(sprite, MissileSprite):
                #if sprite.missile.trajectory:
                    #pygame.draw.line(
                        #pan.image, color.white,
                        #sprite.rect.center,
                        #sprite.destination.center
                        #)

    def create_mooncrete_sprite(self, mooncrete, flyin_position):
        """
        Create a mooncrete sprite.

        """

        rect = self.convert_moonscape_to_panel(mooncrete.position)
        cargo = MooncreteSprite(rect)
        cargo.image = self.placeholder_pix(
            MOONSCAPE_BLOCK_SIZE, color.darker_gray)
        self.courier_send_sprite(
            mooncrete.id, cargo, flyin_position, mooncrete.position)

    def destroy_mooncrete_sprite(self, mooncrete):
        """
        Destroy a mooncrete sprite.

        """

        if self.moonbase_sprites.has_key(mooncrete.id):
            del self.moonbase_sprites[mooncrete.id]

    def create_turret_sprite(self, turret, flyin_position):
        """
        Create a turret sprite.

        """

        # TODO use dedicated turret sprite
        rect = self.convert_moonscape_to_panel(turret.position)
        cargo = Sprite('turret', rect)
        cargo.turret = turret
        cargo.image = self.placeholder_pix(
            MOONSCAPE_BLOCK_SIZE, color.gold)
        self.courier_send_sprite(
            turret.id, cargo, flyin_position, turret.position)

    def destroy_turret_sprite(self, turret):
        """
        Destroy a turret sprite.

        """

        if self.moonbase_sprites.has_key(turret.id):
            del self.moonbase_sprites[turret.id]

    def create_radar_sprite(self, radar, flyin_position):
        """
        Create a radar sprite.

        """

        # TODO use dedicated radar sprite
        rect = self.convert_moonscape_to_panel(radar.position)
        cargo = Sprite('radar', rect)
        cargo.radar = radar
        cargo.image = self.placeholder_pix(
            MOONSCAPE_BLOCK_SIZE, color.copper)
        self.courier_send_sprite(
            radar.id, cargo, flyin_position, radar.position)

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

        # TODO use a dedicated AsteroidSprite here.
        # No fancy sliding movement required please.
        position = self.convert_moonscape_to_panel(asteroid.position)
        rect = pygame.Rect(position, MOONSCAPE_BLOCK_SIZE)
        sprite = Sprite('asteroid %s' % (asteroid.id,), rect)

        # use a placehold image
        pix = pygame.Surface(MOONSCAPE_BLOCK_SIZE)
        pix.fill(color.red)
        sprite.addimage(pix, 1, -1)

        self.arcade_sprites[asteroid.id] = sprite
        trace.write('asteroid created at %s' % (rect))

    def move_asteroid(self, asteroid):
        """
        Move the given model asteroid sprite.

        """

        sprite = self.arcade_sprites.get(asteroid.id, None)
        if sprite:
        # convert indexes to screen coordinates
            x, y = asteroid.position
            x = x * ARCADE_VIEW_MODEL_RATIO[0]
            y = y * ARCADE_VIEW_MODEL_RATIO[1]
            sprite.rect.topleft = (x, y)
            #sprite.set_position((x, y))

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
        rect = pygame.Rect(position, MOONSCAPE_BLOCK_SIZE)
        # destination used by the sprite to calc it's angle of rotation
        dest_coords = self.convert_arcade_to_screen(missile.destination)
        destination = pygame.Rect((0, 0), MOONSCAPE_BLOCK_SIZE)
        destination.center = dest_coords
        # use a placehold image
        pix = pygame.Surface(MOONSCAPE_BLOCK_SIZE)
        pix.fill(color.purple)
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
