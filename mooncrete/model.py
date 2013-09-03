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

    def escape_state(self):
        """
        Escape from the current state.

        """

        self.change_state(None)

    def begin_or_continue(self):
        """
        Begins a new game or continue one in progress.

        """

        self.change_state(STATE_PHASE1)
        # queues the help state to only post after our model gets unpaused.
        self.chain_event(StateEvent(STATE_HELP))

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


CALCIUM_BARREL = 1
WATER_BARREL = 2
EMPTY_BARREL = 3
MOONROCKS = 4
RADAR_CIRCUITS = 10
RADAR_DISH = 11
RADAR = 12
TURRET_BASE = 20
TURRET_MUNITION = 21
TURRET = 22
MOONCRETE_SLAB_1 = 30
MOONCRETE_SLAB_2 = 30
BUILDING_1 = 40
BUILDING_2 = 40
PHASE1_PIECES = (CALCIUM_BARREL, WATER_BARREL, EMPTY_BARREL)
PHASE2_PIECES = (RADAR_CIRCUITS, RADAR_DISH, TURRET_BASE, TURRET_MUNITION, MOONROCKS)


class PuzzleBlock(object):
    """
    Contains information for a single puzzle block.

    """

    def __init__(self):
        self.block_type = None
        self.x = None
        self.y = None


class PuzzleGrid(object):
    """
    Contains the puzzle grid information and handles play logic.

    """

    def __init__(
                self,
                size,
                block_spawned_callback,
                block_moved_callback,
                block_removed_callback,
                grid_full_callback,
                ):
        self.size = size
        self.grid = None
        self.clear_grid()
        self.block_spawned_callback = block_spawned_callback
        self.block_moved_callback = block_moved_callback
        self.block_removed_callback = block_removed_callback
        self.grid_full_callback = grid_full_callback

    def clear_grid(self):
        self.grid = [[None,] * size[1] for i in range(0, size[0])]

    def in_bounds(self, x, y):
        return (x >= 0 and x < self.size[0] and y >= 0 and y < self.size[1])

    def move_a_block(self, block, x_offset, y_offset):
        """
        Move a block by the given offset.
        Handles collisions with other blocks.
        """

        x = block.x + y_offset
        y = block.y + x_offset
        if self.in_bounds(x, y):
            collider = self.grid[x][y]
            if collider:
                # do type checking
                pass
            else:
                self.grid[block.x][block.y] = None
                block.y = y
                self.grid[block.x][block.y] = block
                self.block_moved_callback(block)

    def update(self):
        """
        Update the puzzle grid, dropping any blocks that are able to.

        """

        for v in range(self.size[1], -1, -1):
            for u in range(self.size[0], -1, -1):
                block = self.grid[x][y]
                x = block.x
                y = block.y + 1
                self.move_block(block, x, y)

    def spawn_block(self, block_types):
        """
        Spawn a block of choice block_types.

        """

        # find the first open starting position.
        locs = range(0, self.size[0] - 1)
        random.shuffle(locs)
        while len(locs) > 0:
            x = locs.pop()
            y = 0
            if not self.grid[x][y]:
                block = PuzzleBlock()
                block.block_type = random.choice(block_types)
                block.x = x
                block.y = y
                self.grid[x][y] = block
                self.block_spawned_callback(block)
                return True
        # if no positions are left the grid is full.
        self.grid_full_callback()
