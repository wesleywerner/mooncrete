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
from statemachine import *
from eventmanager import *


FPS = 30


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
        self.sprites = {}
        self.panels = {}
        self.windowsize = None

    def notify(self, event):
        """
        Called by an event in the message queue.
        
        """

        if isinstance(event, TickEvent):
            self.render()
            self.clock.tick(FPS)

        elif isinstance(event, InitializeEvent):
            self.initialize()

        elif isinstance(event, QuitEvent):
            self.isinitialized = False

    def initialize(self):
        """
        Set up for our visuals live here.
        
        """
        
        self.isinitialized = False
        # our coded game size
        self.game_area = pygame.Rect(0, 0, 800, 600)
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
        target_size = self.game_area.size
        flags = 0
        if self.fullscreen:
            # use native monitor resolution
            target_size = (0, 0)
            flags = FULLSCREEN
        self.screen = pygame.display.set_mode(target_size, flags)
        # TODO calculate the native res to game_area height ratio
        #       and store it for scaling the render later.
        # center the game area within the monitor
        self.game_area.topleft = (
            (self.screen.get_width() - self.game_area.width) / 2,
             (self.screen.get_height() - self.game_area.height) / 2,)

        # load resources
        self.image = pygame.Surface(self.game_area.size)
        
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
        
        menu_panel = Panel((100, 300), self.game_area)
        menu_panel.show_position = (0, 0)
        menu_panel.hide_position = (500, 0)
        menu_panel.position = (0, 0)
        self.panels['menu'] = menu_panel

        score_panel = Panel((100, 50), self.game_area)
        score_panel.show_position = (300, 0)
        score_panel.hide_position = (300, -50)
        score_panel.position = (300, -50)
        score_panel.hide()
        self.panels['score'] = score_panel

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

        state = self.model.state.peek()
        
        if state == STATE_MENU:
            pass

        elif state == STATE_HELP:
            pass

        elif state == STATE_LOSE:
            pass

        elif state == STATE_WIN:
            pass

        elif state in (STATE_PHASE1, STATE_PHASE2):
            pass

        elif state == STATE_PHASE3:
            pass

        self.image.fill((0, 128, 0))

        # update panels
        self.transitioning = False
        for key, panel in self.panels.items():
            if panel.draw(self.image):
                self.transitioning = True
        
        pix = self.smallfont.render('hello, world!', False, color.white, color.magenta)
        pix.set_colorkey(color.magenta)
        self.image.blit(pix, (15, 15))
        self.screen.blit(self.image, self.game_area)
        pygame.display.flip()
    
    def hidemenu(self):
        for key, panel in self.panels.items():
            if panel.showing:
                panel.hide()
            else:
                panel.show()

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
        # True while we are busy moving panels around
        self.transitioning = False
    
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
    
    def show(self):
        self.showing = True
        
    def hide(self):
        self.showing = False
    
    def move(self):
        """
        Update our position if necessary.
        
        """
        
        print(self.rect, self.destination)
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
