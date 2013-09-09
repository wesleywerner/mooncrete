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


PUZZLE_WIDTH = 10
PUZZLE_HEIGHT = 10
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
        self.player_score = 0
        self.player_level = 0
        self.player_wave = 0
        # list of blocks in the puzzle playfield not under player control
        self._puzzle_playfield = None
        # matrix of player controlled blocks in their shape
        self._player_blocks = None

    def _puzzle_block_at(self, x, y):
        """
        Get a puzzle block at x y.

        """

        for block in self._puzzle_playfield:
            if block.x == x and block.y == y:
                return block

    def notify(self, event):
        """
        Called by an event in the message queue.

        """

        if isinstance(event, TickEvent):
            if not self.paused:
                self._unchain_events()

        elif isinstance(event, StepGameEvent):
            if not self.paused:
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

        if not self._puzzle_playfield:
            # there is no game to continue
            self._reset_scores()
            self._puzzle_playfield = []
            self.change_state(STATE_PHASE1)
            self._puzzle_drop_random_blocks(FLOTSAM)
            ## TODO chain help event
            #self._chain_event(StateEvent(STATE_HELP))
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
            event = self.event_chain.pop()
            if isinstance(event, StateEvent):
                self.change_state(event.state)
            else:
                self.evman.Post(event)

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
            self._puzzle_drop_random_blocks(FLOTSAM)
        elif self.player_phase == STATE_PHASE2:
            self.player_phase = STATE_PHASE3
            self.change_state(STATE_PHASE3, swap_state=True)
            self._puzzle_drop_random_blocks(FLOTSAM)
        elif self.player_phase == STATE_PHASE3:
            self.player_level += 1
            self.player_phase = STATE_PHASE1
            self.change_state(STATE_PHASE1, swap_state=True)
        ## TODO chain help event
        #if self.player_level == 1:
            #self._chain_event(StateEvent(STATE_HELP))

    def step_game(self):
        """
        Step the game logic.

        """

        if self.paused:
            return
        state = self.state.peek()
        if state in (STATE_PHASE1, STATE_PHASE2):
            self._puzzle_step()

#-- Puzzle Game Logic -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def _puzzle_spawn_player_piece(self, block_types=None):
        """
        Create a new pair of puzzle pieces and make them active
        for player control.

        """

        # default block types
        if not block_types:
            if self.player_phase == STATE_PHASE1:
                block_types = PHASE1_PIECES
            elif self.player_phase == STATE_PHASE2:
                block_types = PHASE2_PIECES
            else:
                trace.write('There are no puzzle pieces for phase %s' % (self.player_phase,))
                return

        # the player piece is a 2D matrix of the blocks in a shape
        shapes = (
                [[0, 1, 0],
                 [1, 1, 1],
                ],
                [[1, 0],
                 [1, 0],
                 [1, 1],
                ],
                [[1, 1],
                 [0, 1],
                ],
                [[1],
                 [1],
                 [1],
                ],
            )

        new_shape = random.choice(shapes)
        # start at top centered
        start_x = (PUZZLE_WIDTH - len(new_shape[0])) / 2
        start_y = 0

        # we index the matrix y then x as to translate the shape so it
        # ends up appearing like drawn above
        for y, row in enumerate(new_shape):
            for x, value in enumerate(row):
                if value:
                    block = PuzzleBlock()
                    block.x = start_x + x
                    block.y = start_y + y
                    block.block_type = random.choice(block_types)
                    new_shape[y][x] = block
                    self._puzzle_block_spawned_callback(block)

        self._player_blocks = new_shape

    def _puzzle_drop_random_blocks(self, block_types):
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
            # find the first open starting position.
            locs = range(0, PUZZLE_WIDTH)
            random.shuffle(locs)
            while len(locs) > 0:
                x = locs.pop()
                y = 0
                if not self._puzzle_block_at(x, y):
                    block = PuzzleBlock()
                    block.block_type = random.choice(block_types)
                    block.x = x
                    block.y = y
                    self._puzzle_playfield.append(block)
                    self._puzzle_block_spawned_callback(block)
                    break

    def _puzzle_in_bounds(self, x, y):
        return (x >= 0 and x < PUZZLE_WIDTH and y >= 0 and y < PUZZLE_HEIGHT)

    def _puzzle_step(self):
        """
        Update the puzzle, dropping any blocks that are able to.

        """

        # auto move playfield blocks from the bottom up, so chain reaction falling
        # can happend
        for y in reversed(range(0, PUZZLE_HEIGHT)):
            for x in reversed(range(0, PUZZLE_HEIGHT)):
                block = self._puzzle_block_at(x, y)
                if block:
                    new_y = block.y + 1
                    if self._puzzle_in_bounds(block.x, new_y):
                        collider = self._puzzle_block_at(x, new_y)
                        if collider:
                            # do type checking
                            pass
                        else:
                            self._puzzle_update_block_position(block, block.x, new_y)

        self._puzzle_move_player_pieces(0, 1)

        trace.write(self._puzzle_print_grid())

    def _puzzle_move_player_pieces(self, x_offset, y_offset):
        """
        Move player controlled pieces as a whole.

        """

        if not self._player_blocks:
            return
        add_to_playfield = False
        valid_move = True
        for row in self._player_blocks:
            for block in row:
                if block:
                    new_x = block.x + x_offset
                    new_y = block.y + y_offset
                    if not self._puzzle_in_bounds(new_x, new_y):
                        valid_move = False
                        if (x_offset, y_offset) == (0, 1):
                            # hit the bottom
                            add_to_playfield = True
                    else:
                        collider = self._puzzle_block_at(new_x, new_y)
                        if collider:
                            # is moving downwards
                            if (x_offset, y_offset) == (0, 1):
                                # hit something at the bottom
                                add_to_playfield = True
                            else:
                                # just a sideways collision
                                valid_move = False

        if valid_move and not add_to_playfield:
            for row in self._player_blocks:
                for block in row:
                    if block:
                        self._puzzle_update_block_position(block, block.x + x_offset, block.y + y_offset)

        if add_to_playfield:
            for row in self._player_blocks:
                for block in row:
                    if block:
                        self._puzzle_playfield.append(block)
            self._player_blocks = None

    def _puzzle_print_grid(self):
        grid = []
        for y in range(0, PUZZLE_HEIGHT):
            grid.append('\n')
            for x in range(0, PUZZLE_HEIGHT):
                block = self._puzzle_block_at(x, y)
                if block:
                    grid.append(str(block.block_type))
                else:
                    grid.append('_')
        return ' '.join(grid)

    def _puzzle_update_block_position(self, block, x, y):
        """
        Use this to set a block's XY.
        It updates the puzzle grid and the block together.

        """

        block.x = x
        block.y = y
        self._puzzle_block_moved_callback(block)

    def puzzle_rotate_cw(self):
        """
        Rotate the active puzzle pieces clockwise.

        """

        b1, b2 = self._active_puzzle_pieces
        if not b1 and not b2:
            return
        # rotate b2 around b1
        x_offset, y_offset = None, None
        if (b1.x < b2.x) and (b1.y == b2.y):
            x_offset = -1
            y_offset = 1
        elif (b1.x == b2.x) and (b1.y < b2.y):
            x_offset = -1
            y_offset = -1
        elif (b1.x > b2.x) and (b1.y == b2.y):
            x_offset = 1
            y_offset = -1
        elif (b1.x == b2.x) and (b1.y > b2.y):
            x_offset = 1
            y_offset = 1
        if not x_offset and not y_offset:
            return
        x = b2.x + x_offset
        y = b2.y + y_offset
        if (self._puzzle_in_bounds(x, y) and not self._puzzle_block_at(x, y)):
            self._puzzle_move_block(b2, x_offset, y_offset)

    def puzzle_rotate_ccw(self):
        """
        Rotate the active puzzle pieces clockwise.

        """

        b1, b2 = self._active_puzzle_pieces
        if not b1 and not b2:
            return
        # rotate b2 around b1
        x_offset, y_offset = None, None
        if (b1.x < b2.x) and (b1.y == b2.y):
            x_offset = -1
            y_offset = -1
        elif (b1.x == b2.x) and (b1.y < b2.y):
            x_offset = 1
            y_offset = -1
        elif (b1.x > b2.x) and (b1.y == b2.y):
            x_offset = 1
            y_offset = 1
        elif (b1.x == b2.x) and (b1.y > b2.y):
            x_offset = -1
            y_offset = 1
        if not x_offset and not y_offset:
            return
        x = b2.x + x_offset
        y = b2.y + y_offset
        if (self._puzzle_in_bounds(x, y) and not self._puzzle_block_at(x, y)):
            self._puzzle_move_block(b2, x_offset, y_offset)

    def puzzle_move_left(self):
        """
        Move the active puzzle piece left.

        """

        self._puzzle_move_player_pieces(-1, 0)

    def puzzle_move_right(self):
        """
        Move the active puzzle piece left.

        """

        self._puzzle_move_player_pieces(1, 0)

    def _puzzle_block_spawned_callback(self, block):
        """
        An interface to link block actions with system events.

        """

        trace.write('block %s was spawned' % (block.id,))
        self.evman.Post(PuzzleBlockSpawnedEvent(block))

    def _puzzle_block_moved_callback(self, block):
        """
        An interface to link block actions with system events.

        """

        #trace.write('block %s was moved %s' % (block.id, (block.x, block.y)))
        self.evman.Post(PuzzleBlockMovedEvent(block))

    def _puzzle_block_removed_callback(self, block):
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

