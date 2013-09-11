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
        self.model_update_delay = 1000
        self.last_model_update = 0

    def can_step_model(self):
        """
        Limits the model update frequency.
        (Updating each Tick would be too fast a game, of course!)

        """

        ticks = pygame.time.get_ticks()
        if ticks - self.last_model_update > self.model_update_delay:
            self.last_model_update = ticks
            return True

    def notify(self, event):
        """
        Called by an event in the message queue.

        """

        if isinstance(event, TickEvent):

            # update the model pause state
            self.model.paused = self.view.transitioning

            # step the model if it is time
            if self.can_step_model():
                self.evman.Post(StepGameEvent())

            for event in pygame.event.get():

                # always handle window closing events
                if event.type == QUIT:
                    self.evman.Post(QuitEvent())

                # all key downs
                if event.type == KEYDOWN:
                    if event.key == K_F11:
                        self.view.toggle_fullscreen()
                    state = self.model.state
                    if state == STATE_MENU:
                        self.menu_keys(event)
                    elif state in (STATE_PHASE1, STATE_PHASE2):
                        self.puzzle_keys(event)
                    elif state == STATE_PHASE3:
                        self.arcade_keys(event)
                    elif state == STATE_HELP:
                        self.help_keys(event)
                    else:
                        # allow escaping from unhandled states
                        self.model.escape_state()

    def menu_keys(self, event):

        if event.key == K_ESCAPE:
            self.model.escape_state()

        elif event.key == K_SPACE:
            self.model.new_or_continue()

    def puzzle_keys(self, event):

        if event.key == K_ESCAPE:
            self.model.escape_state()

        elif event.key in (K_x,):
            self.model.rotate_puzzle()

        elif event.key in (K_a, K_LEFT):
            self.model.move_left()

        elif event.key in (K_a, K_RIGHT):
            self.model.move_right()

        elif event.key in (K_DOWN,):
            self.model.move_down()

        elif event.key == K_F2:
            self.model._next_phase()

        elif event.key == K_F3:
            self.model._puzzle_spawn_player_piece()

    def arcade_keys(self, event):

        if event.key == K_ESCAPE:
            self.model.escape_state()

        elif event.key == K_F2:
            self.model._next_phase()

    def help_keys(self, event):

        if event.key == K_ESCAPE:
            self.model.escape_state()
