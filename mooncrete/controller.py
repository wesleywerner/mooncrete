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
import helper
from pygame.locals import *
from statemachine import *
from eventmanager import *


# the seconds of play the player has per phase
PLAYTIME = {
    STATE_PHASE1: 30,
    STATE_PHASE2: 30,
    STATE_PHASE3: 90,
    STATE_REPRIEVE: 5,
    }

# arcade game speed per game level.
# levels higher than the max will be clamped.
ARCADE_SPEEDS = (50, 46, 42, 38, 34, 30, 26, 22, 20)

# puzzle game speed per game level.
PUZZLE_SPEEDS = (1000, 950, 900, 850, 800, 750, 700, 650, 600, 550, 500, 450, 400, 350)

# a user event for ticker over the menu counter.
# used for animating main menu score drawing.
MENU_TICK_EVENT = pygame.USEREVENT + 0


class MoonController(object):
    """
    Handles everything about user input: mouse and keyboard.

    """

    def __init__(self, eventmanager, model, view):
        self.evman = eventmanager
        self.evman.RegisterListener(self)
        self.model = model
        self.view = view
        self.puzzle_update_freq = PUZZLE_SPEEDS[0]
        self.arcade_update_freq = ARCADE_SPEEDS[0]
        self.last_model_update = 0
        self.stopwatch = 0
        self.time_left = 0

    def can_step_model(self, ticks, model_state):
        """
        Limits the model update frequency.
        (Updating each Tick would be too fast a game, of course!)

        """

        # the puzzle and arcade modes have different speeds
        if model_state in (STATE_PHASE1, STATE_PHASE2):
            frequency = self.puzzle_update_freq
        elif model_state in (STATE_PHASE3, STATE_LOSE, STATE_REPRIEVE):
            frequency = self.arcade_update_freq
        else:
            return

        if ticks - self.last_model_update > frequency:
            self.last_model_update = ticks
            return True

    def playtime_countdown(self, ticks, model_state):
        """
        Update the time the player has left for the current phase.
        This also triggers the next phase when time is up.

        """

        # check if 1 second has passed since last time.
        if (ticks - self.stopwatch > 1000):
            self.stopwatch = ticks
            self.time_left -= 1
            self.view.set_time_left(self.time_left)
        else:
            return

        # has enough time passed for this phase?
        max_time = PLAYTIME.get(model_state, 0)
        if (max_time and self.time_left == 0):
            self.time_left = max_time
            self.model._next_phase()

    def notify(self, event):
        """
        Called by an event in the message queue.

        """

        if isinstance(event, TickEvent):

            ticks = pygame.time.get_ticks()
            state = self.model.state

            # update the model pause state
            self.model.paused = self.view.transitioning

            # step the model if it is time
            if self.can_step_model(ticks, state):
                self.evman.Post(StepGameEvent())
                # update the playtime countdown
                self.playtime_countdown(ticks, state)

            for event in pygame.event.get():

                # always handle window closing events
                if event.type == QUIT:
                    self.evman.Post(QuitEvent())

                # all key downs
                if event.type == KEYDOWN:

                    if event.key == K_F11:
                        self.view.toggle_fullscreen()

                    if state == STATE_MENU:
                        self.menu_keys(event)

                    elif state in (STATE_PHASE1, STATE_PHASE2):
                        self.puzzle_keys(event)

                    elif state in (STATE_PHASE3, STATE_REPRIEVE):
                        self.arcade_keys(event)

                    elif state == STATE_LEVELDONE:
                        self.level_done_keys(event)

                    elif state == STATE_HELP:
                        self.help_keys(event)

                    else:
                        # allow escaping from unhandled states
                        if (event.key in (K_ESCAPE, K_RETURN, K_SPACE)):
                            self.model.escape_state()

                elif event.type == MOUSEBUTTONDOWN:

                    if state in (STATE_PHASE3, STATE_REPRIEVE):
                        pos = self.view.convert_screen_to_arcade(event.pos)
                        self.model.fire_missile(pos)

                elif event.type == MENU_TICK_EVENT:
                    self.view.menu_ticker_step()

        elif isinstance(event, StateEvent):

            # reset the time passed counter on state changes
            self.time_left = PLAYTIME.get(self.model.state, 0)

            # set the arcade speed per level
            speed_index = helper.clamp(self.model.level - 1, 0, len(ARCADE_SPEEDS) - 1)
            self.arcade_update_freq = ARCADE_SPEEDS[speed_index]

            # set the puzzle speed per level
            speed_index = helper.clamp(self.model.level - 1, 0, len(PUZZLE_SPEEDS) - 1)
            self.puzzle_update_freq = PUZZLE_SPEEDS[speed_index]

            # set a menu timer for text animations
            if event.state == STATE_MENU:
                pygame.time.set_timer(MENU_TICK_EVENT, 1000)
            else:
                pygame.time.set_timer(MENU_TICK_EVENT, 0)

    def menu_keys(self, event):

        if event.key == K_ESCAPE:
            self.model.escape_state()

        elif event.key == K_SPACE:
            self.model.new_or_continue()

    def puzzle_keys(self, event):

        if event.key == K_ESCAPE:
            self.model.escape_state()

        elif event.key in (K_x,):
            self.model.rotate_puzzle(clockwise=True)

        elif event.key in (K_z,):
            self.model.rotate_puzzle(clockwise=False)

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

    def level_done_keys(self, event):

        if event.key in (K_ESCAPE, K_SPACE):
            self.model._next_phase()

    def help_keys(self, event):

        if event.key == K_ESCAPE:
            self.model.escape_state()
