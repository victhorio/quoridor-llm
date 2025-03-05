"""
Implementation of the actual quoridor game mechanics.
"""

from enum import Enum
from dataclasses import dataclass
from collections import deque
import copy

from . import constants


@dataclass(frozen=True)
class Pos:
    row: int
    col: int

    def __add__(self, other: "Pos") -> "Pos":
        return Pos(self.row + other.row, self.col + other.col)


@dataclass
class Player:
    pos: Pos
    wall_balance: int


class Dir(Enum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3

    def as_pos_delta(self) -> Pos:
        if self == Dir.UP:
            return Pos(1, 0)
        if self == Dir.DOWN:
            return Pos(-1, 0)
        if self == Dir.LEFT:
            return Pos(0, -1)
        if self == Dir.RIGHT:
            return Pos(0, 1)

        assert False, "unreachable code after exhaustive checks"


class Edges:
    _cells = list[bool]
    rows: int
    cols: int

    def __init__(self, rows: int, cols: int):
        self._cells = [False] * rows * cols
        self.rows = rows
        self.cols = cols

    def __call__(self, pos: Pos) -> bool:
        return self._cells[pos.row * self.cols + pos.col]

    def set(self, pos: Pos) -> None:
        idx = pos.row * self.cols + pos.col
        assert not self._cells[idx], "Placing a wall on top of another wall"
        self._cells[idx] = True


class GameState:
    """
    game state implementation
    """

    # the row wall index (i,j) represents whether the TOP edge of the game cell (i,j)
    # therefore there are BOARD_CELL_DIM_COUNT - 1 rows (the top row doesn't have a top edge) and
    # there are BOARD_CELL_DIM_COUNT columns
    edges_up: Edges
    # the col wall index (i,j) represents whether the RIGHT edge of a the game cell (i,j)
    # therefore there are BOARD_CELL_DIM_COUNT rows and there are BOARD_CELL_DIM_COUNT - 1 columns
    # since the rightmost column doesn't have a right edge
    edges_right: Edges
    # stores the player information
    players: tuple[Player, Player]

    def __init__(self, edges_up: Edges, edges_right: Edges, player_a: Player, player_b: Player):
        assert edges_up.cols == constants.BOARD_GRID_SIZE
        assert edges_up.rows == constants.BOARD_GRID_SIZE - 1

        assert edges_right.cols == constants.BOARD_GRID_SIZE - 1
        assert edges_right.rows == constants.BOARD_GRID_SIZE

        self.edges_up = edges_up
        self.edges_right = edges_right
        self.players = (player_a, player_b)

    @classmethod
    def new_game(cls):
        player_start_col = int(constants.BOARD_GRID_SIZE / 2)
        return cls(
            edges_up=Edges(constants.BOARD_GRID_SIZE - 1, constants.BOARD_GRID_SIZE),
            edges_right=Edges(constants.BOARD_GRID_SIZE, constants.BOARD_GRID_SIZE - 1),
            player_a=Player(Pos(0, player_start_col), constants.PLAYER_WALL_START_COUNT),
            player_b=Player(Pos(constants.BOARD_GRID_SIZE - 1, player_start_col), constants.PLAYER_WALL_START_COUNT),
        )

    @staticmethod
    def _wall_canonical_index(pos: Pos, direction: Dir) -> tuple[Pos, Dir]:
        # if the direction is not `up` or `right`, we change the reference position `pos`
        # so that we refer to the same wall, but now with an `up` or `right` direction
        if direction in (Dir.UP, Dir.RIGHT):
            pos_canonical, direction_canonical = pos, direction
        elif direction == Dir.LEFT:
            pos_canonical, direction_canonical = pos + Dir.LEFT.as_pos_delta(), Dir.RIGHT
        elif direction == Dir.DOWN:
            pos_canonical, direction_canonical = pos + Dir.DOWN.as_pos_delta(), Dir.UP
        else:
            assert False, "unreachable code"

        # TODO: let's check for OOB before returning
        return pos_canonical, direction_canonical

    def wall_check(self, pos: Pos, direction: Dir) -> bool:
        pos, direction = GameState._wall_canonical_index(pos, direction)

        if direction == Dir.UP:
            return self.edges_up(pos)
        if direction == Dir.RIGHT:
            return self.edges_right(pos)

        assert False, "unreachable code"

    def wall_place(self, pos: Pos, direction: Dir) -> None:
        pos, direction = GameState._wall_canonical_index(pos, direction)

        if direction == Dir.UP:
            self.edges_up.set(pos)
            return
        if direction == Dir.RIGHT:
            self.edges_right.set(pos)
            return

        assert False, "unreachable code"

    def wall_placement_blocks(self, pos: Pos, direction: Dir) -> bool:
        """
        Returns whether a `wall_place(pos, direction)` would completely block the path for either
        of the players reaching the opposite edge.
        """
        pos_canonical, direction_canonical = GameState._wall_canonical_index(pos, direction)

        # Check if wall placement is valid (not on top of another wall)
        if direction_canonical == Dir.UP and self.edges_up(pos_canonical):
            return True  # Wall already exists, can't place
        if direction_canonical == Dir.RIGHT and self.edges_right(pos_canonical):
            return True  # Wall already exists, can't place

        # TODO: This is too expensive, but during initial implementation I just don't want to worry
        #       about mutating the actual game (temporarily) and perhaps leaving it in a bad state
        #       if there's an error somewhere in between before we undo changes

        # Let's add the wall and check if it makes it unreachable
        game_counterfactual = copy.deepcopy(self)
        if direction_canonical == Dir.UP:
            game_counterfactual.edges_up.set(pos_canonical)
        elif direction_canonical == Dir.RIGHT:
            game_counterfactual.edges_right.set(pos_canonical)
        else:
            assert False, "unreachable code"

        print("CHECKING CURRENT CONFIGURATION:")
        game_counterfactual.print()

        if not game_counterfactual._player_can_reach_goal(0):
            return True
        if not game_counterfactual._player_can_reach_goal(1):
            return True
        return False

    def _player_can_reach_goal(self, player_idx: int) -> bool:
        """
        Checks if the player can reach their goal using BFS, returning True if it's reachable.
        """
        # Get the player position and target row
        player_pos = self.players[player_idx].pos
        enemy_pos = self.players[1 - player_idx].pos
        target_row = constants.BOARD_GRID_SIZE - 1 if player_idx == 0 else 0

        print(f"{enemy_pos = }")

        # Set up BFS
        queue = deque([player_pos])
        visited = set([(player_pos.row, player_pos.col)])

        while queue:
            pos = queue.popleft()

            # have we reached the target?
            if pos.row == target_row:
                print(f"reached {pos = }")
                return True

            # try all possible moves from here
            for direction in [Dir.UP, Dir.DOWN, Dir.LEFT, Dir.RIGHT]:
                new_pos = pos + direction.as_pos_delta()

                # we disregard this new position on the following conditions, noting that checking
                # oob before walls is important to avoid oob accesses
                if new_pos == enemy_pos:
                    # note that this check is too conservative because while the enemy may block the
                    # path right now, it could sidestep in the future, however since there are non
                    # sidestepabble possibilities, i'd rather be conservative
                    #
                    # to illustrate, this condition means that this scenario will fail:
                    #
                    #     +   +   +   +   +   +   +   +   +   +
                    #  8                  | 1
                    #     +   +   +   +   +   +   +   +   +   +
                    #  7                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  6                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  5                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  4                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  3                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  2                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  1                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  0                  | 0 |
                    #     +   +   +   +   +   +   +   +   +   +
                    #       0   1   2   3   4   5   6   7   8
                    #
                    # because player 0 is unable to reach the edge right now IF player 1 doesn't
                    # move, but player 1 would obviously move
                    #
                    # the concern is that in this scenario:
                    #     +   +   +   +   +   +   +   +   +   +
                    #  8                  | 1 |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  7                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  6                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  5                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  4                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  3                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  2                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  1                  |   |
                    #     +   +   +   +   +   +   +   +   +   +
                    #  0                  | 0 |
                    #     +   +   +   +   +   +   +   +   +   +
                    #       0   1   2   3   4   5   6   7   8
                    #
                    # we really want to fail because the players cannot sidestep one another
                    #
                    # NOTE: think about how to do this more intelligently in the future, sounds like
                    #       an interesting problem
                    continue
                if not self._is_position_inbounds(new_pos):
                    continue
                if (new_pos.row, new_pos.col) in visited:
                    continue
                if self.wall_check(pos, direction):
                    continue

                # it's valid, so we want to explore from it
                queue.append(new_pos)
                visited.add((new_pos.row, new_pos.col))

        # nothing else to look at, so we couldn't reach our target
        return False

    def _is_position_inbounds(self, pos: Pos) -> bool:
        return 0 <= pos.row < constants.BOARD_GRID_SIZE and 0 <= pos.col < constants.BOARD_GRID_SIZE

    def move(self, player_idx: int, direction: Dir) -> tuple[bool, str]:
        player_pos_cur = self.players[player_idx].pos
        player_pos_new = player_pos_cur + direction.as_pos_delta()

        # Check if the new position is within the board boundaries
        if not self._is_position_inbounds(player_pos_new):
            return False, "Cannot move outside the board boundaries"

        # Check if there's a wall blocking the move
        if self.wall_check(player_pos_cur, direction):
            return False, "Cannot move through a wall"

        # Check player collision
        assert len(self.players) == 2, "Invalid Assumption: unexpected number of players"
        enemy_idx = 1 - player_idx  # (player_idx == 1) ? 0 : 1
        enemy_pos = self.players[enemy_idx].pos
        if player_pos_new == enemy_pos:
            return False, "Tried to move to a cell already occupied by other player"

        # Update the player's position
        self.players[player_idx].pos = player_pos_new

        # Check for win condition
        # Player A wins by reaching the top row (row 8)
        if player_idx == 0 and player_pos_new.row == constants.BOARD_GRID_SIZE - 1:
            return False, ""
        # Player B wins by reaching the bottom row (row 0)
        elif player_idx == 1 and player_pos_new.row == 0:
            return False, ""

        # Valid move, no win
        return True, ""

    def print(self):
        """Prints an ASCII representation of the board and walls"""

        GRID_SIZE = constants.BOARD_GRID_SIZE
        player_map = {player.pos: f" {idx} " for idx, player in enumerate(self.players)}
        empty_row_str = "    " + "+   " * GRID_SIZE + "+"

        # we start from the top row, which is the highest index, and go down from there
        for row in range(GRID_SIZE)[::-1]:
            # print a full line with the top walls first, unless we're in the absolute top row
            # in which case we don't have top walls
            if row == GRID_SIZE - 1:
                print(empty_row_str)
            else:
                row_str = "    "
                for col in range(GRID_SIZE):
                    row_str += "+"
                    row_str += "---" if self.edges_up(Pos(row, col)) else "   "
                row_str += "+"
                print(row_str)

            # print the walls and its cells
            # 4 characters for alignment, plus an empty space for the emtpy left-most wall
            cell_row_str = f"{row:2d}   "
            for col in range(GRID_SIZE):
                pos = Pos(row, col)
                cell_row_str += player_map.get(pos, "   ")
                cell_row_str += " " if col == GRID_SIZE - 1 or not self.edges_right(pos) else "|"

            print(cell_row_str)

        # show the bottom row and its coordinates
        print(empty_row_str)
        row_coord_str = "    "
        for col in range(GRID_SIZE):
            row_coord_str += f" {col:2d} "
        print(row_coord_str)
