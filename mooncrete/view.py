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
        pix = self.smallfont.render('hello, world!', False, color.white, color.magenta)
        pix.set_colorkey(color.magenta)
        self.image.blit(pix, (15, 15))
        self.screen.blit(self.image, self.game_area)
        pygame.display.flip()
        
