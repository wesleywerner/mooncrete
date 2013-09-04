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

        if isinstance(event, StepGameEvent):
            if not self.paused:
                self._unchain_events()
                self.step_game()

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

    def change_state(self, new_state, swap_state=False):
        """
        Change the model state, and notify the other peeps about this.

        """

        if new_state:
            if swap_state:
                self.state.swap(new_state)
            else:
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
            self._reset_scores()
            self._clear_puzzle_grid()
            self.change_state(STATE_PHASE1)
            if self.auto_help:
                self._chain_event(StateEvent(STATE_HELP))
        else:
            if self.state.peek() == self.player_phase:
                self.change_state(None)
            else:
                self.change_state(self.player_phase)

    def _chain_event(self, next_event):
        """
        Chains an event to be posted on the next (unpaused) Tick.

        """

        self.paused = True
        self.event_chain.insert(0, next_event)

    def _unchain_events(self):
        """
        Removes events from the chain and post them.

        """

        if self.event_chain:
            self.evman.Post(self.event_chain.pop())

    def _reset_scores(self):
        """
        Spam spam spam spam spam spam spam.
        """

        trace.write('reset player scores')
        self.player_score = 0
        self.player_level = 1
        self.player_phase = STATE_PHASE1

    def _next_phase(self):
        """
        Moves to the next phase.

        """

        if self.player_phase == STATE_PHASE1:
            self.player_phase = STATE_PHASE2
            self.change_state(STATE_PHASE2, swap_state=True)
            self._drop_random_blocks(FLOTSAM)
        elif self.player_phase == STATE_PHASE2:
            self.player_phase = STATE_PHASE3
            self.change_state(STATE_PHASE3, swap_state=True)
            self._drop_random_blocks(FLOTSAM)
        elif self.player_phase == STATE_PHASE3:
            self.player_level += 1
            self.player_phase = STATE_PHASE1
            self.change_state(STATE_PHASE1, swap_state=True)

    def step_game(self):
        """
        Step the game logic.

        """

        state = self.state.peek()
        if state in (STATE_PHASE1, STATE_PHASE2):
            self._update_puzzle_grid()

#-- Puzzle Game Logic -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def _clear_puzzle_grid(self):
        trace.write('clearing puzzle grid')
        self._puzzle_grid = [[None,] * PUZZLE_SIZE[1]
                for i in range(0, PUZZLE_SIZE[0])]
        self._drop_random_blocks(FLOTSAM)

    def _drop_random_blocks(self, block_type_list):
        """
        Drop an amount of random block types into the grid, as obstructions
        to the player. These are fast fallers and are not controlled by the
        player keys.

        """

        amount = 2
        if self.player_level > 5:
            amount = 3
        if self.player_level > 10:
            amount = 4
        trace.write('adding %s random blocks to the puzzle grid' % (amount,))

        for n in range(0, amount):
            self._spawn_block(block_type_list)

    def _puzzle_in_bounds(self, x, y):
        return (x >= 0 and x < PUZZLE_SIZE[0] and y >= 0 and y < PUZZLE_SIZE[1])

    def _move_block(self, block, x_offset, y_offset):
        """
        Move a block by the given offset.
        Handles collisions with other blocks, generates events on these.
        """

        x = block.x + x_offset
        y = block.y + y_offset
        if self._puzzle_in_bounds(x, y):
            collider = self._puzzle_grid[x][y]
            if collider:
                # do type checking
                pass
            else:
                self._puzzle_grid[block.x][block.y] = None
                block.y = y
                self._puzzle_grid[block.x][block.y] = block
                self._block_moved_callback(block)

    def _update_puzzle_grid(self):
        """
        Update the puzzle grid, dropping any blocks that are able to.

        """

        trace.write(self._print_puzzle_grid())
        for y in reversed(range(0, PUZZLE_SIZE[1])):
            for x in reversed(range(0, PUZZLE_SIZE[0])):
                block = self._puzzle_grid[x][y]
                if block:
                    self._move_block(block, 0, 1)

    def _print_puzzle_grid(self):
        grid = []
        for y in range(0, PUZZLE_SIZE[1]):
            grid.append('\n')
            for x in range(0, PUZZLE_SIZE[0]):
                block = self._puzzle_grid[x][y]
                if block:
                    grid.append(str(block.block_type))
                else:
                    grid.append('_')
        return ' '.join(grid)

    def _spawn_block(self, block_types):
        """
        Spawn a block of choice block_types.

        """

        # find the first open starting position.
        locs = range(0, PUZZLE_SIZE[0])
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
                self._block_spawned_callback(block)
                return True
        # if no positions are left the grid is full.
        self._puzzle_grid_full_callback()

    def _block_spawned_callback(self, block):
        """
        An interface to link block actions with system events.

        """

        trace.write('block %s was spawned' % (block.id,))
        self.evman.Post(PuzzleBlockSpawnedEvent(block))

    def _block_moved_callback(self, block):
        """
        An interface to link block actions with system events.

        """

        trace.write('block %s was moved %s' % (block.id, (block.x, block.y)))
        self.evman.Post(PuzzleBlockMovedEvent(block))

    def _block_removed_callback(self, block):
        """
        An interface to link block actions with system events.

        """

        trace.write('block %s was removed' % (block.id,))
        pass

    def _puzzle_grid_full_callback(self):
        """
        An interface to link block actions with system events.

        """

        trace.write('The puzzle grid is full. Spam spam spam.')
        pass



#-- Arcade Game Logic -- -- -- -- -- -- -- -- -- -- -- -- -- --

