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


import pygame
from pygame.locals import *
from statemachine import *
from eventmanager import *


class MoonController(object):
    """
    Handles everything about user input: mouse and keyboard.
    
    """
    
    def __init__(self, eventmanager, model, view):
        self.evman = eventmanager
        self.evman.RegisterListener(self)
        self.model = model
        self.view = view

    def notify(self, event):
        """
        Called by an event in the message queue.
        
        """

        if isinstance(event, TickEvent):
            
            # update the model pause state
            self.model.paused = self.view.transitioning
            
            for event in pygame.event.get():
            
                # always handle window closing events
                if event.type == QUIT:
                    self.evman.Post(QuitEvent())

                # all key downs
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        self.model.escape_state()
                    elif event.key == K_F11:
                        self.view.toggle_fullscreen()
                    elif event.key == K_F2:
                        self.view.hidemenu()
                    elif event.key == K_SPACE:
                        self.model.begin_or_continue()