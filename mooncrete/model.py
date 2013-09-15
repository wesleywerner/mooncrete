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
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# A note on imports
#
# I allow myself the luxury to import * as:
#   + eventmanager has every class use the "SpamEvent" convention.
#   + statemachine has all constants named "STATE_SPAM"
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# A note on data attribute names
#
# Data attributes meant only for internal access are prefixed with "_".
# Not that you _can't_ access them, but you should not change them for fear
# of treading on the model's workflow.
#
# http://docs.python.org/2/tutorial/classes.html#random-remarks
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# Puzzle board description
#
# The puzzle board data is stored as a list of lists, allowing a 2D grid-like
# lookup of values. Each value is either 0 (no block) or a number equals one
# of the BLOCK_ constants.
#
# A 3x3 board:
# [[0, 0, 0],
#  [0, 0, 0],
#  [0, 0, 0]]
#
# It can be iterated over for each row, then for each value in that row.
# The puzzle_board_data() function does this and yields the index of each item
# along with the value, for easily accessing the board data:
#
#   for x, y, value in puzzle_board_data():
#       pass
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# Puzzle piece description
#
# The puzzle piece the player controls is stored similarly, in a 2D like list
# of smaller dimensions with the values being those of the BLOCK_ constants.
#
# A T-shape block
# [[1, 1, 1],
#  [0, 1, 0]]
#
# The puzzle_location var stores where the player piece is currently located
# within the board. The player can move it around, as long as the new location
# does not collide with any solid values on the board.
# The _puzzle_move_piece() and _puzzle_piece_collides() calls handle this.
#
# Each game step the puzzle piece is dropped down, if there is a collision
# during this drop, we merge the player piece into the board, and the player
# is given a new piece to play with. This is handled by the _puzzle_merge_board()
# and _puzzle_next_shape() calls.
#
# If there is a collision during creating the new piece, it means the board
# is full to the point where the puzzle has ended.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# Arcade Moonscape
#
#

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -



import copy
import random
import trace
from statemachine import *
from eventmanager import *


# The puzzle mode uses index positioning.
PUZZLE_WIDTH = 10
PUZZLE_HEIGHT = 10

# The arcade mode uses pixel positioning.
# Views rendering this need to scale the results to match the
# actual window size that they are drawing to.
ARCADE_WIDTH = 1000
ARCADE_HEIGHT = 1000

# The moonscape is the rocky moon surface where your base is built.
# It is uses index positioning.
MOONSCAPE_WIDTH = 20
MOONSCAPE_HEIGHT = 6

# different kind of puzzle blocks
BLOCK_CALCIUM_BARREL = 10
BLOCK_WATER_BARREL = 11
BLOCK_MOONCRETE_SLAB = 12
BLOCK_RADAR_BITS = 13
BLOCK_RADAR_DISH = 14
BLOCK_RADAR = 15
BLOCK_TURRET_BASE = 16
BLOCK_TURRET_AMMO = 17
BLOCK_TURRET = 18
BLOCK_BUILDING = 19
BLOCK_EMPTY_BARREL = 20
BLOCK_MOONROCKS = 21

# our block type names
BLOCK_NAMES = {
    BLOCK_CALCIUM_BARREL: 'extracted calcium',
    BLOCK_WATER_BARREL: 'extracted water',
    BLOCK_MOONCRETE_SLAB: 'mooncrete slab',
    BLOCK_RADAR_BITS: 'radar circuits',
    BLOCK_RADAR_DISH: 'radar base',
    BLOCK_RADAR: 'radar',
    BLOCK_TURRET_BASE: 'turret base',
    BLOCK_TURRET_AMMO: 'turret ammo',
    BLOCK_TURRET: 'gun turret',
    BLOCK_BUILDING: 'moon base',
    BLOCK_EMPTY_BARREL: 'empty barrel',
    BLOCK_MOONROCKS: 'moon rocks',
    }

# blocks that make up phase 1 puzzle pieces
PHASE1_PIECES = (
    BLOCK_CALCIUM_BARREL,
    BLOCK_WATER_BARREL,
    )

# blocks that make up phase 2 puzzle pieces
PHASE2_PIECES = (
    BLOCK_RADAR_BITS,
    BLOCK_RADAR_DISH,
    BLOCK_TURRET_BASE,
    BLOCK_TURRET_AMMO,
    )

# block that have no purpose except to obstruct the player
FLOTSAM = (
    BLOCK_EMPTY_BARREL,
    BLOCK_MOONROCKS
    )

# blocks that when combined make a new block
BLOCK_PAIRS = {
    BLOCK_MOONCRETE_SLAB:
        (BLOCK_CALCIUM_BARREL, BLOCK_WATER_BARREL),
    BLOCK_RADAR:
        (BLOCK_RADAR_BITS, BLOCK_RADAR_DISH),
    BLOCK_TURRET:
        (BLOCK_TURRET_AMMO, BLOCK_TURRET_BASE),
    }

# can only place blocks on top of other specific block
BLOCK_BASES = {
    BLOCK_MOONCRETE_SLAB: BLOCK_MOONROCKS,
    BLOCK_RADAR: BLOCK_MOONCRETE_SLAB,
    BLOCK_TURRET: BLOCK_MOONCRETE_SLAB,
    }

# percentage of jutting moonscape features
MOONSCAPE_RUGGEDNESS = 0.3

TETRIS_SHAPES = [
    [[1, 1, 1],
     [0, 1, 0]],

    [[0, 2, 2],
     [2, 2, 0]],

    [[3, 3, 0],
     [0, 3, 3]],

    [[4, 0, 0],
     [4, 4, 4]],

    [[0, 0, 5],
     [5, 5, 5]],

    [[6, 6, 6, 6]],

    [[7, 7],
     [7, 7]]
    ]


class Player(object):
    """
    Stores player infos like score and level.

    """

    def __init__(self):
        self.score = 0
        self.level = 1


class MoonModel(object):
    """
    Handles game logic. Everything data lives in here.

    """

    def __init__(self, eventmanager):
        self._evman = eventmanager
        self._evman.RegisterListener(self)
        self._state = StateMachine()
        self._pumping = False

        # the model can chain events to fire after another.
        # this is done by inserting an event in the chain queue just after
        # firing some other events. The model is paused on chaining.
        # It should unpause via a controller, detailed next...
        self._event_chain = []

        # A paused model does not process any game related actions.
        # Even chained events wait in queue until unpaused.
        # Generally you will want to set this pause flag from a controller
        # while any views are busy animating themselves (transitions etc).
        #   Controller -> model.paused = views.is_busy_animating
        self.paused = False

        # stores current player score and level
        self.player = None

        # stores the last game scores for historics
        self.previous_player = None

        # stores the puzzle board
        self._puzzle_board = None

        # current puzzle shape the player is controlling.
        self._puzzle_shape = None

        # location on the board of the puzzle shape.
        self._puzzle_location = None

        # stores the arcade field
        self.arcade_field = None

        # track the last phase the game was in for continuing games from the menu
        self._last_phase = STATE_MENU

    @property
    def state(self):
        """
        A property that gives the current model state

        """

        return self._state.peek()

    def notify(self, event):
        """
        Called by an event in the message queue.

        """

        if isinstance(event, TickEvent):
            if not self.paused:
                self._unchain_events()

        elif isinstance(event, StepGameEvent):
            if not self.paused:
                state = self._state.peek()
                if state in (STATE_PHASE1, STATE_PHASE2):
                    self._puzzle_step()

        elif isinstance(event, QuitEvent):
            trace.write('Engine shutting down...')
            self._pumping = False
            self.paused = True

    def run(self):
        """
        Kicks off the main engine loop.
        This guy tells everyone else to get ready, and then pumps
        TickEvents to each listener until our pump is turned off.

        """

        trace.write('Initializing...')
        self._evman.Post(InitializeEvent())
        trace.write('Starting the engine pump...')
        self._change_state(STATE_MENU)
        self._pumping = True
        while self._pumping:
            self._evman.Post(TickEvent())

        # wow that was easy, huh?
        # If you are confused as to where things go from here:
        # Each of our model, view and controllers is now constantly
        # receiving TickEvents. Check the notify() calls in each.
        # If you'd like to know more on using the mvc pattern in games
        # see my tutorial on this at:
        # https://github.com/wesleywerner/mvc-game-design :]

#-- Model State Management -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def _change_state(self, new_state, swap_state=False):
        """
        Change the model state, and notify the other peeps about this.

        """

        if new_state:
            # remember the last game phase
            if new_state in (STATE_PHASE1, STATE_PHASE2, STATE_PHASE3):
                self._last_phase = new_state
            # swap the current state for another
            if swap_state:
                self._state.swap(new_state)
            else:
                self._state.push(new_state)
            self._evman.Post(StateEvent(new_state))
        else:
            # remove the current state. If no states remain we quit.
            self._state.pop()
            new_state = self._state.peek()
            if new_state:
                self._evman.Post(StateEvent(new_state))
            else:
                # there is nothing left to pump
                self._evman.Post(QuitEvent())

        ## TODO auto chain help screens for main game phases if this is a new game
        #if new_state in (STATE_PHASE1, STATE_PHASE2, STATE_PHASE3) and
                        #self.player_level == 1:
            #self._chain_event(StateEvent(STATE_HELP))

    def escape_state(self):
        """
        Escape from the current state.

        """

        self._change_state(None)

    def new_or_continue(self):
        """
        Begins a new game or continue one in progress.

        """

        if not self.player:
            # start a new game
            self._change_state(STATE_PHASE1)
            self._reset_game()
        else:
            # continue the game with the last known player phase
            if self.state != self._last_phase:
                self._change_state(self._last_phase)

    def end_game(self):
        """
        Ends the current game.

        """

        # keep a copy of the last game player
        self.previous_player = copy.copy(self.player)
        self.player = None
        self._change_state(STATE_LOSE, swap_state=True)

    def _chain_event(self, next_event):
        """
        Chains an event to be posted on the next (unpaused) Tick.

        """

        self.paused = True
        self._event_chain.insert(0, next_event)

    def _unchain_events(self):
        """
        Removes events from the chain and post them.

        """

        if self._event_chain:
            event = self._event_chain.pop()
            #TODO can we move this isinstance test to the notify() call?
            if isinstance(event, StateEvent):
                self._change_state(event.state)
            else:
                self._evman.Post(event)

    def _next_phase(self):
        """
        Moves to the next phase.

        """

        if self.state == STATE_PHASE1:
            self._change_state(STATE_PHASE2, swap_state=True)
        elif self.state == STATE_PHASE2:
            self._change_state(STATE_PHASE3, swap_state=True)
        elif self.state == STATE_PHASE3:
            self._change_state(STATE_LEVELDONE, swap_state=True)
        elif self.state == STATE_LEVELDONE:
            self.player.level += 1
            self._change_state(STATE_PHASE1, swap_state=True)

    def _reset_game(self):
        """
        Ready all game objects for a new fun filled time.

        """

        self.player = Player()
        self._reset_puzzle()
        self._reset_arcade()

    def _unshared_copy(self, inList):
        """
        Recursive copy list-of-lists.
        Because deepcopy keeps list references and changing the result
        also changes the original.

        """

        if isinstance(inList, list):
            return list(map(self._unshared_copy, inList))
        return inList

#-- Puzzle Game Logic -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def _puzzle_print_grid(self):
        if trace.TRACE and self.player:
            grid = []
            # copy the board and place th player piece inside it
            matrix = self._puzzle_merge_board(
                    self._puzzle_board,
                    self._puzzle_shape,
                    self._puzzle_location
                    )
            for y, row in enumerate(matrix):
                grid.append('\n')
                for x, val in enumerate(row):
                    if val:
                        grid.append(str(val))
                    else:
                        grid.append('__')
            trace.write(' '.join(grid))

    def puzzle_board_data(self, include_player_shape=True):
        """
        Yields the puzzle board data in the form:

            (x, y, value)

        Where value is one of the BLOCK_ constants.

        This can easily be iterated with something like:

            for x, y, v in this_function():

        """

        if include_player_shape:
            grid = self._puzzle_merge_board(
                        self._puzzle_board, self._puzzle_shape, self._puzzle_location)
        else:
            grid = self._puzzle_board
        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                yield (x, y, cell)

    def _reset_puzzle(self):
        """
        Reset the puzzle game.

        """

        # create a new puzzle board
        self._puzzle_board = [[0 for x in xrange(PUZZLE_WIDTH)]
                                for y in xrange(PUZZLE_HEIGHT)]

        # TODO add some random elements for higher levels

        # choose a shape
        self._puzzle_next_shape()

    def _puzzle_merge_board(self, board, shape, shape_location):
        """
        Merge the shape with the board at location and return the new board.
        """
        clone = self._unshared_copy(board)
        x, y = shape_location
        for cy, row in enumerate(shape):
            for cx, val in enumerate(row):
                # NOTE the y-component had a -1
                # assuming since the origin code added an extra line
                # of blocking values to detect collisions near the bottom
                # of the playfield. so if something is fishy, this is it.
                clone[cy + y - 0][cx + x] += val
        return clone

    def _puzzle_next_shape(self):
        """
        Set the player puzzle shape.

        """

        # list of available piece types for the current phase
        piece_types = self._puzzle_allowed_block_types(include_flotsam=False)
        if not piece_types:
            trace.write('state %s does not have puzzle shapes to choose from' % (self.state,))
            return

        # choose a shape and center it
        new_shape = random.choice(TETRIS_SHAPES)
        self._puzzle_shape = new_shape
        self._puzzle_location = [int(PUZZLE_WIDTH / 2 - len(new_shape[0])/2), 0]

        # replace each shape element with a game piece
        for cy, row in enumerate(new_shape):
            for cx, val in enumerate(row):
                if val:
                    new_shape[cy][cx] = random.choice(piece_types)

        # game over if this new piece collides on entry
        collides = self._puzzle_piece_collides(
            self._puzzle_board,
            self._puzzle_shape,
            self._puzzle_location
            )
        if collides:
            self.end_game()

    def _puzzle_allowed_block_types(self, include_flotsam=True):
        """
        Give the list of possible block types for the current player phase.

        """

        pieces = []
        if include_flotsam:
            pieces = list(FLOTSAM)
        if self.state == STATE_PHASE1:
            pieces = pieces + list(PHASE1_PIECES)
        if self.state == STATE_PHASE2:
            pieces = pieces + list(PHASE2_PIECES)
        return pieces

    def _puzzle_in_bounds(self, x, y):
        """
        Checks if a point is in playfield boundaries.

        """

        return (x >= 0 and x < PUZZLE_WIDTH and y >= 0 and y < PUZZLE_HEIGHT)

    def _puzzle_step(self):
        """
        Update the puzzle, dropping any blocks that are able to.

        """

        self._puzzle_drop_piece()
        self._puzzle_pair_blocks()
        self._puzzle_drop_board()

    def _puzzle_drop_piece(self):
        """
        Drop the player puzzle piece.

        """

        new_loc = self._puzzle_location[:]
        new_loc[1] += 1

        collides = self._puzzle_piece_collides(
            self._puzzle_board,
            self._puzzle_shape,
            new_loc
            )

        if collides:

            # merge the shape into the board
            self._puzzle_board = self._puzzle_merge_board(
                self._puzzle_board,
                self._puzzle_shape,
                self._puzzle_location)

            # give the player a new shape to play with
            self._puzzle_next_shape()

        else:
            # no collisions, keep the new drop location
            self._puzzle_location = new_loc
            self._puzzle_print_grid()

    def _puzzle_drop_board(self):
        """
        Drops any floating board pieces down one position.

        """

        for y in xrange(PUZZLE_HEIGHT - 2, -1, -1):
            for x in xrange(PUZZLE_WIDTH):
                if y < PUZZLE_HEIGHT - 1:
                    below = self._puzzle_block_at(x, y + 1)
                    if not below:
                        self._puzzle_board[y + 1][x] = self._puzzle_board[y][x]
                        self._puzzle_board[y][x] = 0

    def _puzzle_piece_collides(self, board, shape, offset):
        """
        Test if the given shape collides with any solids on the board.

        """

        x, y = offset
        for cy, row in enumerate(shape):
            for cx, cell in enumerate(row):
                try:
                    if cell and board[cy + y][cx + x]:
                        return True
                except IndexError:
                    return True
        return False

    def _puzzle_pair_blocks(self):
        """
        Find and remove matching blocks on the board.

        """

        # for each board value (minus the last column and last row)
        #   get the values to the A) right and B) bottom.
        #   ? are the values different
        #   ? are both in a block pair list
        #   remove them and spawn the combined block in the arcade structure

        for new_block, combo in BLOCK_PAIRS.items():
            for x, y, this_block in self.puzzle_board_data(include_player_shape=False):
                # if this block is a possible combination value
                if (this_block in combo):
                    # get the right and bottom neighbors
                    nx = x + 1
                    ny = y + 1
                    xneigh = self._puzzle_block_at(nx, y)
                    yneigh = self._puzzle_block_at(x, ny)
                    # match blocks if they are not the same value
                    # and both exist in the combination list
                    # match the bottom neighbor
                    if yneigh != this_block and yneigh in combo:
                        self._puzzle_clear_cell(x, y)
                        self._puzzle_clear_cell(x, ny)
                        self._arcade_spawn_block(new_block, (x, ny))
                        # skip the next test and
                        # continue with the next board item
                        continue
                    if xneigh != this_block and xneigh in combo:
                        self._puzzle_clear_cell(x, y)
                        self._puzzle_clear_cell(nx, y)
                        self._arcade_spawn_block(new_block, (x, y))

    def _puzzle_block_at(self, x, y):
        """
        Get the block value at x, y.
        Returns None if x, y is out of range.

        """

        if x < PUZZLE_WIDTH and y < PUZZLE_HEIGHT:
            return self._puzzle_board[y][x]

    def _puzzle_clear_cell(self, x, y):
        """
        Clears the board cell at x, y.

        """

        # TODO store the old value and fire an event indicating removal.
        old_value = self._puzzle_board[y][x]
        trace.write('removing "%s" (%s, %s)' %
            (BLOCK_NAMES[old_value], x, y))
        self._puzzle_board[y][x] = 0

    def _puzzle_move_piece(self, delta_x):
        """
        Move the player puzzle piece in a horizontal space.

        """

        x, y = self._puzzle_location[:]
        x += delta_x
        if x < 0:
            x = 0

        collides = self._puzzle_piece_collides(
            self._puzzle_board,
            self._puzzle_shape,
            [x, y]
            )

        if not collides:
            # no collisions, keep the new drop location
            self._puzzle_location = [x, y]
            self._puzzle_print_grid()

    def rotate_puzzle(self, clockwise=True):

        new_shape = self._unshared_copy(self._puzzle_shape)

        if clockwise:
            new_shape = [[new_shape[y][x]
                        for y in xrange(len(new_shape) - 1, -1, -1)]
                        for x in xrange(len(new_shape[0]))]
        else:
            new_shape = [[new_shape[y][x]
                        for y in xrange(len(new_shape))]
                        for x in xrange(len(new_shape[0]) - 1, -1, -1)]

        collides = self._puzzle_piece_collides(
            self._puzzle_board,
            new_shape,
            self._puzzle_location
            )
        if not collides:
            self._puzzle_shape = new_shape
            self._puzzle_print_grid()

    def move_left(self):
        """
        Move the puzzle piece left.

        """

        if self.paused or not self.player:
            return
        if self.state in (STATE_PHASE1, STATE_PHASE2):
            self._puzzle_move_piece(-1)

    def move_right(self):
        """
        Move the puzzle piece left.

        """

        if self.paused:
            return
        if self.state in (STATE_PHASE1, STATE_PHASE2):
            self._puzzle_move_piece(1)

    def move_down(self):
        """
        Move the puzzle piece down.

        """

        if self.paused:
            return
        if self.state in (STATE_PHASE1, STATE_PHASE2):
            self._puzzle_drop_piece()


#-- Arcade Game Logic -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def _reset_arcade(self):
        """
        Reset the arcade game.

        """

        # create a new arcade moonscape.
        # the bottom row will be filled with Moonrock blocks.
        self._moonscape = [
            [BLOCK_MOONROCKS if y == MOONSCAPE_HEIGHT - 1 else 0
            for x in xrange(MOONSCAPE_WIDTH)]
            for y in xrange(MOONSCAPE_HEIGHT)]

        # place some random features on the surface
        for y in xrange(MOONSCAPE_HEIGHT - 2, MOONSCAPE_HEIGHT - 4, -1):
            for x in xrange(MOONSCAPE_WIDTH):
                if random.random() < MOONSCAPE_RUGGEDNESS:
                    is_empty = self._moonscape[y][x]
                    has_base = self._moonscape[y + 1][x]
                    if not is_empty and has_base:
                        self._moonscape[y][x] = BLOCK_MOONROCKS

        self._evman.Post(MoonscapeGeneratedEvent())
        self._arcade_print_moonscape()

    def _moonscape_block_at(self, x, y):
        """
        Get the block value at x, y.
        Returns None if x, y is out of range.

        """

        if x < MOONSCAPE_WIDTH and y < MOONSCAPE_HEIGHT:
            return self._moonscape[y][x]

    def _arcade_print_moonscape(self):
        if trace.TRACE:
            grid = []
            for y, row in enumerate(self._moonscape):
                grid.append('\n')
                for x, val in enumerate(row):
                    if val:
                        grid.append(str(val))
                    else:
                        grid.append('__')
            trace.write(' '.join(grid))

    def _arcade_spawn_block(self, block_type, source_loc):
        """
        Spawn the given block type into the arcade playfield.
        This call takes care fo finding a place for it.

        """

        # 1. pick a random column
        # 2. move down until we hit a moonrock base
        # 3. place the tile on the moonscape
        # 4. fire an event with the tile details.

        # get the required base block we can place this block on
        required_base = BLOCK_BASES.get(block_type, None)
        if not required_base:
            trace.write('Warning: "%s" does not have a BLOCK_BASES entry.' %
                        (BLOCK_NAMES[block_type],))

        found_home = False
        x_range = list(xrange(0, MOONSCAPE_WIDTH))
        random.shuffle(x_range)
        for x in x_range:
            if found_home:
                break
            for y in xrange(0, MOONSCAPE_HEIGHT):
                base = self._moonscape_block_at(x, y + 1)
                if base == required_base:
                    found_home = True
                    self._moonscape[y][x] = block_type
                    spawn_event = ArcadeBlockSpawnedEvent(
                        source_loc, (x, y), block_type, BLOCK_NAMES[block_type])
                    self._evman.Post(spawn_event)
                    break
                elif base:
                    # this is some other kind of block. try another column.
                    break
        else:
            # there are no more open moonrocks to build on
            trace.write('There are no "%s" blocks to place "%s" on' %
                (BLOCK_NAMES[required_base], BLOCK_NAMES[block_type]))

        self._arcade_print_moonscape()

    def moonscape_data(self):
        for y, row in enumerate(self._moonscape):
            for x, cell in enumerate(row):
                yield (x, y, cell)
