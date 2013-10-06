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


import math
import copy
import random
import trace
import helper
from gameObjects import *
from statemachine import *
from eventmanager import *


# The puzzle mode uses index positioning.
PUZZLE_WIDTH = 15
PUZZLE_HEIGHT = 15

# The arcade size is in a much more refined scale.
# views should scale accordingly to their screen size.
ARCADE_WIDTH = 300
ARCADE_HEIGHT = 300

# Block padding defines the minimum open blocks between moon base objects.
# This limits moonbase size so instead of having a 100-block moon base
# we limit it to a (100 / 5 = 20) block moon base.
# Setting this to 1 allow you to build a massive base.
# Views that draw the base will need to size their sprites to a ratio of
# the arcade size to block padding accordingly.
BLOCK_PADDING = 15

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
BLOCK_LUNAR_SURFACE = 22

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
    BLOCK_LUNAR_SURFACE: 'lunar surface',
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
    BLOCK_BUILDING:
        (BLOCK_CALCIUM_BARREL, BLOCK_WATER_BARREL),
    }

# define which moon base types can be placed on top of which other types.
# note how it maps a block type to a class type.
BLOCK_BUILD_REQUIREMENTS = {
    BLOCK_MOONCRETE_SLAB: LunarLand,
    BLOCK_BUILDING: LunarLand,
    BLOCK_RADAR: Mooncrete,
    BLOCK_TURRET: Mooncrete,
    }

# percentage of jutting moonscape features
MOONSCAPE_RUGGEDNESS = 0.3

# how high the lunar landscape could go
BASE_HEIGHT = 3

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
        self.level = 0
        self.score = 0
        self.asteroids_destroyed = 0
        self.moonbases_built = 0
        self.moonbases_destroyed = 0
        self.bonus_asteroids = 0
        self.bonus_base = 0
        self.bonus_base_destroyed = 0
        self._last_phase = 0

        # flag if there is a game in progress
        self._playing = False

        # stores the puzzle board
        self._puzzle_board = None

        # current puzzle shape the player is controlling.
        self._puzzle_shape = None

        # location on the board of the puzzle shape.
        self._puzzle_location = None

        # track the last phase the game was in for continuing games from the menu
        self._last_phase = STATE_MENU

        # list of asteroids in the arcade game mode
        self._asteroids = []

        # missiles the player has fired
        self._missiles = []

        # explosions that grow in size
        self._explosions = []

        # store built moonbase objects in a dictionary where the
        # key is the (x, y) position.
        self._moonbase = {}

        # lose sequence explosion fascilitator
        self.lose_sequence_explosion_counter = 0

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
                elif state in (STATE_PHASE3, STATE_LOSE, STATE_REPRIEVE):
                    self._arcade_step()

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
                ## TODO auto chain help screens for main game phases for new games
                #if (self.level == 1):
                    #self._chain_event(StateEvent(STATE_HELP))
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

    def escape_state(self):
        """
        Escape from the current state.

        """

        self._change_state(None)

    def new_or_continue(self):
        """
        Begins a new game or continue one in progress.

        """

        if not self._playing:
            trace.write('starting a new game...')
            self._reset_game()
            self._change_state(STATE_PHASE1)
        else:
            # continue the game with the last known player phase
            if self.state != self._last_phase:
                self._change_state(self._last_phase)

    def end_game(self):
        """
        Ends the current game.

        """

        self._arcade_clear_bonuses()
        self._arcade_destroy_all_your_base()
        self._playing = False
        self.lose_sequence_explosion_counter = 30

        # queue the LOSE state and change to a reprieve
        self._state.swap(STATE_LOSE)
        self._change_state(STATE_REPRIEVE)

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
            self._puzzle_shape = None
            self._arcade_prepare()
            self._change_state(STATE_PHASE3, swap_state=True)

        elif self.state == STATE_PHASE3:
            # queue the LEVELDONE state and change to a reprieve
            self._state.swap(STATE_LEVELDONE)
            self._change_state(STATE_REPRIEVE)
            self._arcade_destroy_all_asteroids()

        elif self.state == STATE_REPRIEVE:
            self._arcade_calculate_score_bonus()
            self._change_state(None)
            #self._change_state(STATE_LEVELDONE, swap_state=True)

        elif self.state == STATE_LEVELDONE:
            self.level += 1
            self._change_state(STATE_PHASE1, swap_state=True)

    def _reset_game(self):
        """
        Ready all game objects for a new fun filled time.

        """

        self._evman.Post(ResetGameEvent())
        self.level = 1
        self.score = 0
        self._reset_puzzle()
        self._arcade_prepare()
        self._generate_lunar_landscape()
        self._playing = True

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
        if trace.TRACE and self._playing:
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

        if include_player_shape and self._puzzle_shape:
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
        self._puzzle_shape = None
        # TODO add some random elements for higher levels

    def _puzzle_merge_board(self, board, shape, shape_location):
        """
        Merge the shape with the board at location and return the new board.

        """

        clone = self._unshared_copy(board)
        x, y = shape_location
        for cy, row in enumerate(shape):
            for cx, val in enumerate(row):
                clone[cy + y][cx + x] += val
        return clone

    def _puzzle_next_shape(self):
        """
        Set the player puzzle shape.

        """

        # list of available piece types for the current phase
        piece_types = self._puzzle_allowed_block_types(include_flotsam=True)
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
        self._puzzle_clear_filled_lines()

        # choose a new puzzle piece
        if not self._puzzle_shape:
            self._puzzle_next_shape()

    def _puzzle_drop_piece(self):
        """
        Drop the player puzzle piece.

        """

        if not self._puzzle_shape:
            return

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

    def _puzzle_clear_filled_lines(self):
        """
        Clears puzzle lines that are filled up.

        """

        for y in xrange(PUZZLE_HEIGHT - 1, -1, -1):
            if self._puzzle_board[y].count(0) == 0:
                for x in xrange(PUZZLE_WIDTH):
                    self._puzzle_board[y][x] = 0
                self._evman.Post(PuzzleRowCleared(row_number=y))
                break

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

        shuffled_pairs = BLOCK_PAIRS.items()
        random.shuffle(shuffled_pairs)
        for new_block, combo in shuffled_pairs:
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
                        self._arcade_build_moonbase(new_block)
                        # skip the next test
                        continue
                    if xneigh != this_block and xneigh in combo:
                        self._puzzle_clear_cell(x, y)
                        self._puzzle_clear_cell(nx, y)
                        self._arcade_build_moonbase(new_block)

    def _puzzle_block_at(self, x, y):
        """
        Get the block value at x, y.
        Returns None if x, y is out of range.

        """

        if self._puzzle_in_bounds(x, y):
            return self._puzzle_board[y][x]

    def _puzzle_clear_cell(self, x, y):
        """
        Clears the board cell at x, y.

        """

        old_value = self._puzzle_board[y][x]
        self._puzzle_board[y][x] = 0

    def _puzzle_move_piece(self, delta_x):
        """
        Move the player puzzle piece in a horizontal space.

        """

        if not self._puzzle_shape:
            return

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

        if not self._puzzle_shape:
            return

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

        if self._playing and not self.paused:
            if self.state in (STATE_PHASE1, STATE_PHASE2):
                self._puzzle_move_piece(-1)

    def move_right(self):
        """
        Move the puzzle piece left.

        """

        if self._playing and not self.paused:
            if self.state in (STATE_PHASE1, STATE_PHASE2):
                self._puzzle_move_piece(1)

    def move_down(self):
        """
        Move the puzzle piece down.

        """

        if self._playing and not self.paused:
            if self.state in (STATE_PHASE1, STATE_PHASE2):
                self._puzzle_drop_piece()


#-- Arcade Game Logic -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def closest_ready_turret(self, arcade_position):
        """
        Returns the closest, charged turret to a position.
        Position is in ARCADE measurements (ARCADE _WIDTH / _HEIGHT).

        """

        # do not allow targeting positions below the boundary.
        if (arcade_position[1] >= ARCADE_HEIGHT - ((BASE_HEIGHT + 4) * BLOCK_PADDING)):
            return

        chosen_one = None
        chosen_dist = ARCADE_HEIGHT
        for key, base in self._moonbase.items():
            if isinstance(base, Turret):
                if base.ready:
                    distance = helper.distance(* arcade_position + base.position)
                    if distance < chosen_dist:
                        chosen_dist = distance
                        chosen_one = base
        return chosen_one

    def fire_missile(self, arcade_position):
        """
        Launch a missile towards to given arcade position, the closest
        ready turret will provide the firing solution.

        """

        turret = self.closest_ready_turret(arcade_position)
        if turret:
            trace.write('firing solution number %s' % (turret.id,))
            turret.charge = 0
            missile = Missile(turret.position, arcade_position)
            self._missiles.append(missile)
            self._evman.Post(MissileSpawnedEvent(missile))
        else:
            trace.write('no ready turrets found')

    def _arcade_destroy_all_your_base(self):
        """
        Self destruct initiated....

        """

        remove_list = []
        for key, base in self._moonbase.items():
            if isinstance(base, Turret):
                self._evman.Post(TurretDestroyEvent(base))
                remove_list.append(base)
            elif isinstance(base, Radar):
                self._evman.Post(RadarDestroyEvent(base))
                remove_list.append(base)
            elif isinstance(base, Mooncrete):
                self._evman.Post(MooncreteDestroyEvent(base))
                remove_list.append(base)
        for dead_base in remove_list:
            del self._moonbase[dead_base.position]

    def _arcade_clear_bonuses(self):
        """
        Clear bonus counters for the level.

        """

        self.asteroids_destroyed = 0
        self.moonbases_built = 0
        self.moonbases_destroyed = 0
        self.bonus_asteroids = 0
        self.bonus_base = 0
        self.bonus_base_destroyed = 0

    def _arcade_prepare(self):
        """
        Prepare the arcade game for a new phase.

        """

        self._arcade_clear_bonuses()

        for explosion in self._explosions:
            self._evman.Post(ExplosionDestroyEvent(explosion))
        for missile in self._missiles:
            self._evman.Post(MissileDestroyEvent(missile))
        self._asteroids = []
        self._explosions = []
        self._missiles = []

        # add some bases for testing
        for n in xrange(5):
            self._arcade_build_moonbase(BLOCK_MOONCRETE_SLAB)
        for n in xrange(3):
            self._arcade_build_moonbase(BLOCK_RADAR)
        for n in xrange(2):
            self._arcade_build_moonbase(BLOCK_TURRET)

    def _arcade_destroy_all_asteroids(self):
        """
        Destroy all asteroids.

        """

        # clear remnant asteroids and missiles and explosions
        for asteroid in self._asteroids:
            self._arcade_spawn_explosion(asteroid.position)
        self._arcade_remove_asteroids(copy.copy(self._asteroids))

    def _generate_lunar_landscape(self):
        """
        Build a lunar land scape.

        """

        self._evman.Post(LunarLandscapeClearedEvent())
        self._moonbase = {}

        # fill the bottom with LunarLands
        for x in xrange(0, ARCADE_WIDTH, BLOCK_PADDING):
            y = ARCADE_HEIGHT - BLOCK_PADDING
            position = (x, y)
            land = LunarLand(position)
            self._moonbase[position] = land
            self._evman.Post(LunarLandSpawnEvent(land))

        # for the next n levels up, place some random LunarLands
        # as dictated by MOONSCAPE_RUGGEDNESS.
        # only place a land if on top of another land.
        rlist = list(self._arcade_iterate_moonscape_blocks(n=BASE_HEIGHT))
        for position in rlist:
            if random.random() < MOONSCAPE_RUGGEDNESS:
                # store all moonbase related objects with a key equals
                # position. don't worry, moon base objects do not overlap.
                x, y = position
                current = self._moonbase.get(position, None)
                base = self._moonbase.get((x, y + BLOCK_PADDING), None)
                if not current and base:
                    land = LunarLand(position)
                    self._moonbase[position] = land
                    self._evman.Post(LunarLandSpawnEvent(land))

    def _arcade_iterate_moonscape_blocks(self, n=5):
        """
        A yielder to iterate over moon base block locations, bottom up
        for n rows.

        This function simply calculates the range to loop through
        bottom up, skipping in block padding steps.

        n=1 is the bottom most row, which is ideally a solid line
        of lunar lands.

        n=2 is where mooncrete can be laid (unless the landscape generated
        randomly placed additional lands on this row too)

        """

        start = ARCADE_HEIGHT - BLOCK_PADDING
        end = ARCADE_HEIGHT - (n + 1) * BLOCK_PADDING
        for y in xrange(start, end, -BLOCK_PADDING):
            for x in xrange(0, ARCADE_WIDTH, BLOCK_PADDING):
                yield (x, y)

    def _arcade_in_bounds(self, position):
        """
        Checks if a point is in arcade boundaries.

        """

        x, y = position
        return (x >= 0 and x < ARCADE_WIDTH and y >= 0 and y < ARCADE_HEIGHT)

    def _moonbase_at(self, position):
        """
        Get the block value at (x, y) position
        or None if the position is empty.

        Since the moon base blocks use padding, we snap the position to
        the closest padding position.

        """

        x, y = position
        x = int(math.floor(float(x) / BLOCK_PADDING) * BLOCK_PADDING)
        y = int(math.floor(float(y) / BLOCK_PADDING) * BLOCK_PADDING)
        return self._moonbase.get((x, y), None)

    def _arcade_build_moonbase(self, block_type):
        """
        Use this to build the moon base.

        It constructs the game object, finds a Destination for it
        and fires matching events.

        """

        # get the required block we can place this block on
        required_base = BLOCK_BUILD_REQUIREMENTS.get(block_type, None)
        if not required_base:
            trace.write('Warning: "%s" does not have a BLOCK_BUILD_REQUIREMENTS entry.' %
                        (BLOCK_NAMES[block_type],))

        # shuffle all possible moon base positions.
        # go through them until we find an open one where the block below
        # (the base) is the required block type.
        home_position = None
        moonbase_positions = list(self._arcade_iterate_moonscape_blocks())
        random.shuffle(moonbase_positions)
        for position in moonbase_positions:
            current = self._moonbase.get(position, None)
            base = self._moonbase.get((position[0], position[1] + BLOCK_PADDING), None)
            if not current and isinstance(base, required_base):
                home_position = position
                break
        if not home_position:
            trace.write('There are no "%s" moon base blocks to place "%s" on' %
                (required_base, BLOCK_NAMES[block_type]))
            return

        # construct game objects
        if block_type == BLOCK_MOONCRETE_SLAB:
            slab = Mooncrete(home_position)
            self._moonbase[home_position] = slab
            self._evman.Post(MooncreteSpawnEvent(
                mooncrete=slab))
        elif block_type == BLOCK_BUILDING:
            self.moonbases_built += 1
            base = Building(home_position)
            self._moonbase[home_position] = base
            self._evman.Post(BuildingSpawnEvent(
                building=base))
        elif block_type == BLOCK_TURRET:
            self.moonbases_built += 1
            turret = Turret(home_position)
            self._moonbase[home_position] = turret
            self._evman.Post(TurretSpawnedEvent(
                turret=turret))
        elif block_type == BLOCK_RADAR:
            self.moonbases_built += 1
            radar = Radar(home_position)
            self._moonbase[home_position] = radar
            self._evman.Post(RadarSpawnedEvent(
                radar=radar))
        else:
            return

    def _arcade_step(self):
        """
        Step the arcade game.

        """

        turrets_alive = 0
        for position, base_object in self._moonbase.items():
            # recharge our gun turrets
            if isinstance(base_object, Turret):
                turrets_alive += 1
                base_object.recharge()

        if (self.state == STATE_PHASE3):
            self._arcade_spawn_asteroids()
        self._arcade_move_asteroids()
        self._arcade_move_missiles()
        self._arcade_grow_explosions()

        # test for lose conditions
        if (self._playing):
            if (turrets_alive == 0):
                self.end_game()
        else:
            if (self.lose_sequence_explosion_counter > 0):
                self.lose_sequence_explosion_counter -= 1
                position = (
                    random.randint(0, ARCADE_WIDTH),
                    random.randint(0, ARCADE_HEIGHT))
                self._arcade_spawn_explosion(position)

    def _arcade_calculate_score_bonus(self):
        """
        Calculate how much bonus score we get.

        """

        self.bonus_asteroids = self.asteroids_destroyed * 10
        self.bonus_base = self.moonbases_built * 5
        self.bonus_base_destroyed = self.moonbases_destroyed * 3
        self.score += self.bonus_asteroids
        self.score += self.bonus_base
        self.score -= self.bonus_base_destroyed

    def _arcade_spawn_asteroids(self):
        """
        Create a new asteroid and put it in play.

        """

        # create n asteroids + level
        min_asteroids = 6
        extra_per_level = 1.5
        total_asteroids = int(min_asteroids + (self.level * extra_per_level))

        # spawn some asteroids
        if (self._playing and len(self._asteroids) < total_asteroids):
            position = (random.randint(0, ARCADE_WIDTH), 0)
            destination = (random.randint(0, ARCADE_WIDTH), ARCADE_HEIGHT)
            # let asteroids target base objects directly on higer levels
            if self.level > 1:
                base_target = self._arcade_get_random_moonbase_target([Turret, Radar, Mooncrete])
                if base_target:
                    destination = base_target
            asteroid = Asteroid(position, destination)
            self._asteroids.append(asteroid)
            self._evman.Post(AsteroidSpawnedEvent(asteroid))

    def _arcade_get_random_moonbase_target(self, type_list):
        """
        Return a random key for a moon base object of the given type list.

        """

        choices = []
        for key, base in self._moonbase.items():
            if type(base) in type_list:
                choices.append(key)
        if choices:
            target = random.choice(choices)
            # center the target by half the padding and ensure it goes beyond
            # the game boundary.
            return (target[0] + (BLOCK_PADDING / 2), ARCADE_HEIGHT)

    def _arcade_move_asteroids(self):
        """
        Move lunar asteroids coming your way.

        """

        # we cannot modify the asteroid list while iterating it.
        # keep track of those to remove after our loop is done.
        remove_list = []
        for asteroid in self._asteroids:

            # move asteroids
            asteroid.move()
            self._evman.Post(AsteroidMovedEvent(asteroid))

            if not self._arcade_in_bounds(asteroid.position):
                # the asteroid is out of the game boundaries
                remove_list.append(asteroid)
            else:
                if self._arcade_destroy_base_at(asteroid.position):
                    remove_list.append(asteroid)

        self._arcade_remove_asteroids(remove_list)

    def _arcade_destroy_base_at(self, position):
        """
        Destroy the base structure at a position.

        If it is a mooncrete object, it will also destroy anything
        built on top of it.

        Returns True if something got hit.

        """

        # get any moon base object at this position
        base_object = self._moonbase_at(position)

        if base_object:

            # check for asteroid + moonbase collisions
            if isinstance(base_object, LunarLand):
                # we hit the ground and disintegrate in a puff of dust
                return True

            elif isinstance(base_object, Mooncrete):
                # we hit a mooncrete slab. destroy both items.
                del self._moonbase[base_object.position]
                self._evman.Post(MooncreteDestroyEvent(base_object))
                self._arcade_destroy_base_at((position[0], position[1] - BLOCK_PADDING))
                return True

            elif isinstance(base_object, Building):
                # we hit a moon base building. destroy both.
                self.moonbases_destroyed += 1
                del self._moonbase[base_object.position]
                self._evman.Post(BuildingDestroyEvent(base_object))
                return True

            elif isinstance(base_object, Turret):
                # we hit a gun turret. destroy both items.
                self.moonbases_destroyed += 1
                del self._moonbase[base_object.position]
                self._evman.Post(TurretDestroyEvent(base_object))
                return True

            elif isinstance(base_object, Radar):
                # we hit a radar dish. destroy both.
                self.moonbases_destroyed += 1
                del self._moonbase[base_object.position]
                self._evman.Post(RadarDestroyEvent(base_object))
                return True

    def _arcade_remove_asteroids(self, asteroid_list):
        """
        Helper to remove a list of asteroids with sanity checks.

        """

        for asteroid in asteroid_list:
            try:
                self._asteroids.remove(asteroid)
                self._evman.Post(AsteroidDestroyEvent(asteroid))
            except ValueError:
                pass

    def _arcade_move_missiles(self):
        """
        Move fired missiles through the lunar air.

        """

        remove_list = []
        for missile in self._missiles:
            if missile.move():
                self._evman.Post(MissileMovedEvent(missile))
            else:
                self._arcade_spawn_explosion(missile.position)
                remove_list.append(missile)

        for missile in remove_list:
            self._missiles.remove(missile)
            self._evman.Post(MissileDestroyEvent(missile))

    def _arcade_grow_explosions(self):
        """
        Grow explosions.

        """

        explosion_remove_list = []
        asteroid_remove_list = []
        new_explosions = []
        for explosion in self._explosions:
            if explosion.update():
                self._evman.Post(ExplosionGrowEvent(explosion))
                # check for collisions with asteroids
                for asteroid in self._asteroids:
                    dist = helper.distance(* asteroid.position + explosion.position)
                    if (dist < explosion.radius * 4):
                        self.asteroids_destroyed += 1
                        asteroid_remove_list.append(asteroid)
                        new_explosions.append(asteroid)
            else:
                explosion_remove_list.append(explosion)

        self._arcade_remove_asteroids(asteroid_remove_list)

        for explosion in explosion_remove_list:
            self._explosions.remove(explosion)
            self._evman.Post(ExplosionDestroyEvent(explosion))
        for asteroid in new_explosions:
            self._arcade_spawn_explosion(asteroid.position)

    def _arcade_spawn_explosion(self, position):
        """
        Spawn a new impact point that grows its explosion.

        """

        explosion = Explosion(position)
        self._explosions.append(explosion)
        self._evman.Post(ExplosionSpawnEvent(explosion))
