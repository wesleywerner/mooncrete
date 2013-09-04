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

# a note on imports: I allow myself the luxury to import * as
# + eventmanager has every class use the SpamEvent naming convention.
# + statemachine has all constants prefixed STATE_SPAM

import random
import trace
from statemachine import *
from eventmanager import *


PUZZLE_SIZE = (5, 5)
CALCIUM_BARREL = 1
WATER_BARREL = 2
EMPTY_BARREL = 3
MOONROCKS = 4
RADAR_BITS = 10
RADAR_DISH = 11
RADAR = 12
TURRET_BASE = 20
TURRET_AMMO = 21
TURRET = 22
MOONCRETE_SLAB = 30
BUILDING = 40
PHASE1_PIECES = (CALCIUM_BARREL, WATER_BARREL, EMPTY_BARREL)
PHASE2_PIECES = (RADAR_BITS, RADAR_DISH, TURRET_BASE, TURRET_AMMO, MOONROCKS)
FLOTSAM = (EMPTY_BARREL, MOONROCKS)

class PuzzleBlock(object):
    def __init__(self):
        self.block_type = None
        self.x = None
        self.y = None

    @property
    def id(self):
        return id(self)

class MoonModel(object):
    """
    Handles game logic. Everything data lives in here.

    """

    def __init__(self, eventmanager):
        self.evman = eventmanager
        self.evman.RegisterListener(self)
        self.state = StateMachine()
        self.is_pumping = False
        self.paused = False
        self.event_chain = []
        self._puzzle_grid = None
        self.player_score = 0
        self.player_level = 0
        self.player_wave = 0
        self.auto_help = True

    def notify(self, event):
        """
        Called by an event in the message queue.

        """

        if isinstance(event, TickEvent):
            if not self.paused:
                self.unchain_events()
                pass

        elif isinstance(event, QuitEvent):
            trace.write('Engine shutting down...')
            self.is_pumping = False
            self.paused = True

    def run(self):
        """
        Kicks off the main engine loop.
        This guy tells everyone else to get ready, and then pumps
        TickEvents to each listener until our pump is turned off.

        """

        trace.write('Initializing...')
        self.evman.Post(InitializeEvent())
        trace.write('Starting the engine pump...')
        self.change_state(STATE_MENU)
        self.is_pumping = True
        while self.is_pumping:
            self.evman.Post(TickEvent())

        # wow that was easy, huh?
        # If you are confused as to where things go from here:
        # Each of our model, view and controllers is now constantly
        # receiving TickEvents. Check the notify() calls in each.
        # If you'd like to know more on using the mvc pattern in games
        # see my tutorial on this at:
        # https://github.com/wesleywerner/mvc-game-design :]

#-- Model State Management -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def change_state(self, new_state):
        """
        Change the model state, and notify the other peeps about this.

        """

        if new_state:
            self.state.push(new_state)
            self.evman.Post(StateEvent(new_state))
        else:
            self.state.pop()
            new_state = self.state.peek()
            if new_state:
                self.evman.Post(StateEvent(new_state))
            else:
                # there is nothing left to pump
                self.evman.Post(QuitEvent())

    def escape_state(self):
        """
        Escape from the current state.

        """

        self.change_state(None)

    def new_game(self):
        """
        Begins a new game or continue one in progress.

        """

        if not self._puzzle_grid:
            # there is no game to continue
            self.reset_scores()
            self.clear_puzzle_grid()
            self.change_state(STATE_PHASE1)
            if self.auto_help:
                self.chain_event(StateEvent(STATE_HELP))
        else:
            self.change_state(self.player_phase)

    def chain_event(self, next_event):
        """
        Chains an event to be posted on the next (unpaused) Tick.

        """

        self.paused = True
        self.event_chain.insert(0, next_event)

    def unchain_events(self):
        """
        Removes events from the chain and post them.

        """

        if self.event_chain:
            self.evman.Post(self.event_chain.pop())

    def reset_scores(self):
        """
        Spam spam spam spam spam spam spam.
        """

        trace.write('reset player scores')
        self.player_score = 0
        self.player_level = 1
        self.player_phase = STATE_PHASE1

    def next_phase(self):
        """
        Moves to the next phase.

        """

        # TODO post game messages in phase changes
        if self.player_phase == STATE_PHASE1:
            self.player_phase = STATE_PHASE2
            self.change_state(STATE_PHASE2)
        elif self.player_phase == STATE_PHASE2:
            self.player_phase = STATE_PHASE3
            self.change_state(STATE_PHASE3)
        elif self.player_phase == STATE_PHASE3:
            self.player_level += 1
            self.player_phase = STATE_PHASE1
            self.change_state(STATE_PHASE1)



#-- Puzzle Game Logic -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def clear_puzzle_grid(self):
        trace.write('clearing puzzle grid')
        self._puzzle_grid = [[None,] * PUZZLE_SIZE[1]
                for i in range(0, PUZZLE_SIZE[0])]

    def drop_random_blocks(self, block_type_list):
        """
        Drop an amount of random block types into the grid, as obstructions
        to the player. These are fast fallers and are not controlled by the
        player keys.

        """

        trace.write('adding %s random blocks to the puzzle grid' % (amount,))

        amount = 2
        if self.player_level > 5:
            amount = 3
        if self.player_level > 10:
            amount = 4

        for n in range(0, amount):
            self.spawn_block(block_type_list)

    def puzzle_in_bounds(self, x, y):
        return (x >= 0 and x < PUZZLE_SIZE[0] and y >= 0 and y < PUZZLE_SIZE[1])

    def move_block(self, block, x_offset, y_offset):
        """
        Move a block by the given offset.
        Handles collisions with other blocks, generates events on these.
        """

        x = block.x + y_offset
        y = block.y + x_offset
        if self.puzzle_in_bounds(x, y):
            collider = self._puzzle_grid[x][y]
            if collider:
                # do type checking
                pass
            else:
                self._puzzle_grid[block.x][block.y] = None
                block.y = y
                self._puzzle_grid[block.x][block.y] = block
                self.block_moved_callback(block)

    def update(self):
        """
        Update the puzzle grid, dropping any blocks that are able to.

        """

        for v in range(PUZZLE_SIZE[1], -1, -1):
            for u in range(PUZZLE_SIZE[0], -1, -1):
                block = self._puzzle_grid[x][y]
                self.move_block(block, 0, 1)

    def spawn_block(self, block_types):
        """
        Spawn a block of choice block_types.

        """

        # find the first open starting position.
        locs = range(0, PUZZLE_SIZE[0] - 1)
        random.shuffle(locs)
        while len(locs) > 0:
            x = locs.pop()
            y = 0
            if not self._puzzle_grid[x][y]:
                block = PuzzleBlock()
                block.block_type = random.choice(block_types)
                block.x = x
                block.y = y
                self._puzzle_grid[x][y] = block
                self.block_spawned_callback(block)
                return True
        # if no positions are left the grid is full.
        self._puzzle_grid_full_callback()

    def block_spawned_callback(self, block):
        """
        An interface to link block actions with system events.

        """

        trace.write('block %s was spawned' % (block.id,))
        pass

    def block_moved_callback(self, block):
        """
        An interface to link block actions with system events.

        """

        trace.write('block %s was moved %s' % (block.id, str(block.x, block.y)))
        pass

    def block_removed_callback(self, block):
        """
        An interface to link block actions with system events.

        """

        trace.write('block %s was removed' % (block.id,))
        pass

    def grid_full_callback(self):
        """
        An interface to link block actions with system events.

        """

        trace.write('The puzzle grid is full. Spam spam spam.')
        pass



#-- Arcade Game Logic -- -- -- -- -- -- -- -- -- -- -- -- -- --

