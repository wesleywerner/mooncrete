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
#
###### A note on imports
# I allow myself the luxury to import * as:
#   + eventmanager has every class use the "SpamEvent" convention.
#   + statemachine has all constants named "STATE_SPAM"
#
###### A note on data attribute names
# Data attributes meant only for internal access are prefixed with "_".
# Not that you _can't_ access them, but you should not change them for fear
# of treading on the model's workflow.
#
# http://docs.python.org/2/tutorial/classes.html#random-remarks
#

import copy
import random
import trace
from statemachine import *
from eventmanager import *


PUZZLE_WIDTH = 10
PUZZLE_HEIGHT = 10
CALCIUM_BARREL = 10
WATER_BARREL = 11
EMPTY_BARREL = 12
MOONROCKS = 13
RADAR_BITS = 14
RADAR_DISH = 15
RADAR = 16
TURRET_BASE = 17
TURRET_AMMO = 18
TURRET = 19
MOONCRETE_SLAB = 20
BUILDING = 21
PHASE1_PIECES = (CALCIUM_BARREL, WATER_BARREL, EMPTY_BARREL)
PHASE2_PIECES = (RADAR_BITS, RADAR_DISH, TURRET_BASE, TURRET_AMMO, MOONROCKS)
FLOTSAM = (EMPTY_BARREL, MOONROCKS)

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
        # current player phase.
        self.phase = STATE_PHASE1
        # current puzzle shape the player is controlling.
        self.puzzle_shape = None
        # location on the board of the puzzle shape.
        self.puzzle_location = None


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
            self._reset_game()
            self._change_state(STATE_PHASE1)
        else:
            # continue the game with the last known player phase
            if self.state != self.player.phase:
                self._change_state(self.player.phase)

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

        if self.player_phase == STATE_PHASE1:
            self.player_phase = STATE_PHASE2
            self._change_state(STATE_PHASE2, swap_state=True)
        elif self.player_phase == STATE_PHASE2:
            self.player_phase = STATE_PHASE3
            self._change_state(STATE_PHASE3, swap_state=True)
        elif self.player_phase == STATE_PHASE3:
            self.player.phase == STATE_LEVELDONE
            self._change_state(STATE_LEVELDONE, swap_state=True)
        elif self.player_phase == STATE_LEVELDONE:
            self.player_level += 1
            self.player_phase = STATE_PHASE1
            self._change_state(STATE_PHASE1, swap_state=True)

    def _reset_game(self):
        """
        Ready all game objects for a new fun filled time.

        """

        self.player = Player()
        self._reset_puzzle()
        # TODO reset puzzle board
        # TODO reset arcade field

#-- Puzzle Game Logic -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def _puzzle_print_grid(self):
        if trace.TRACE and self.player:
            grid = []
            # copy the board and place th player piece inside it
            matrix = self._merge_board(
                    self.player.board,
                    self.player.puzzle_shape,
                    self.player.puzzle_location
                    )
            for y, row in enumerate(matrix):
                grid.append('\n')
                for x, val in enumerate(row):
                    if val:
                        grid.append(str(val))
                    else:
                        grid.append('__')
            trace.write(' '.join(grid))

    def _reset_puzzle(self):
        """
        Reset the puzzle game.

        """

        # create a new puzzle board
        self.player.board = [[0 for x in xrange(PUZZLE_WIDTH)]
                                for y in xrange(PUZZLE_HEIGHT)]

        # TODO add some random elements for higher levels

        # choose a shape
        self._puzzle_next_shape()

    def _unshared_copy(self, inList):
        """
        Recursive copy list-of-lists.
        Because deepcopy keeps list references and changing the result
        also changes the original.

        """

        if isinstance(inList, list):
            return list(map(self._unshared_copy, inList))
        return inList

    def _merge_board(self, board, shape, shape_location):
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
        piece_types = self._puzzle_allowed_block_types(include_flotsam=True)
        if not piece_types:
            trace.write('state %s does not have puzzle shapes to choose from' % (state,))
            return

        # choose a shape and center it
        new_shape = random.choice(TETRIS_SHAPES)
        self.player.puzzle_shape = new_shape
        self.player.puzzle_location = [int(PUZZLE_WIDTH / 2 - len(new_shape[0])/2), 0]

        # replace each shape element with a game piece
        for cy, row in enumerate(new_shape):
            for cx, val in enumerate(row):
                if val:
                    new_shape[cy][cx] = random.choice(piece_types)

        # game over if this new piece collides on entry
        collides = self._puzzle_piece_collides(
            self.player.board,
            self.player.puzzle_shape,
            self.player.puzzle_location
            )
        if collides:
            self.end_game()

    def _puzzle_allowed_block_types(self, include_flotsam=True):
        """
        Give the list of possible block types for the current player phase.

        """

        if self.player.phase == STATE_PHASE1:
            return PHASE1_PIECES + FLOTSAM if include_flotsam else []
        if self.player.phase == STATE_PHASE2:
            return PHASE2_PIECES + FLOTSAM if include_flotsam else []

        trace.write('There are no puzzle pieces for phase %s' % (self.player_phase,))

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
        self._puzzle_print_grid()

    def _puzzle_drop_piece(self):
        """
        Drop the player puzzle piece.

        """

        new_loc = self.player.puzzle_location[:]
        new_loc[1] += 1

        collides = self._puzzle_piece_collides(
            self.player.board,
            self.player.puzzle_shape,
            new_loc
            )

        if collides:

            # merge the shape into the board
            self.player.board = self._merge_board(
                self.player.board,
                self.player.puzzle_shape,
                self.player.puzzle_location)

            # give the player a new shape to play with
            self._puzzle_next_shape()

            # TODO check the type of blocks around us to determined
            # if any of them can combine.

        else:
            # no collisions, keep the new drop location
            self.player.puzzle_location = new_loc

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

    def puzzle_rotate_cw(self):
        """
        Rotate the puzzle piece clock wise.

        """

        if self.paused:
            return
        if self.state in (STATE_PHASE1, STATE_PHASE2):
            pass

    def puzzle_rotate_ccw(self):
        """
        Rotate the puzzle piece counter clock wise.

        """

        if self.paused:
            return
        if self.state in (STATE_PHASE1, STATE_PHASE2):
            pass

    def _puzzle_move_piece(self, delta_x):
        """
        Move the player puzzle piece in a horizontal space.

        """

        x, y = self.player.puzzle_location[:]
        x += delta_x
        if x < 0:
            x = 0

        collides = self._puzzle_piece_collides(
            self.player.board,
            self.player.puzzle_shape,
            [x, y]
            )

        if not collides:
            # no collisions, keep the new drop location
            self.player.puzzle_location = [x, y]

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

## Events to be implemented
        #self._evman.Post(PuzzleBlockSpawnedEvent(block))
        #self._evman.Post(PuzzleBlockMovedEvent(block))



#-- Arcade Game Logic -- -- -- -- -- -- -- -- -- -- -- -- -- --

