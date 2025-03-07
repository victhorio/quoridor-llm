"""
Implementation of the actual quoridor game mechanics.
"""

import copy
from collections import deque
from dataclasses import dataclass
from enum import Enum

from . import constants


@dataclass(frozen=True)
class Pos:
    row: int
    col: int

    def __add__(self, other: "Pos") -> "Pos":
        return Pos(self.row + other.row, self.col + other.col)

    def __str__(self) -> str:
        return f"({self.row}, {self.col})"


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
        assert False, "unreachable code"

    def __str__(self) -> str:
        if self == Dir.UP:
            return "up"
        if self == Dir.DOWN:
            return "down"
        if self == Dir.LEFT:
            return "left"
        if self == Dir.RIGHT:
            return "right"
        assert False, "unreachable code"

    @staticmethod
    def from_str(s: str):
        if s == "up":
            return Dir.UP
        if s == "down":
            return Dir.DOWN
        if s == "left":
            return Dir.LEFT
        if s == "right":
            return Dir.RIGHT

        raise ValueError(f"the string `{s}` cannot be parsed as a direction")


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
    # stores the player information
    players: tuple[Player, Player]
    # edges_up and edges_right each store, respectively, a boolean flag indicating if the top/right
    # edge of cell (i, j) has a wall or not, noting that the edges of the board as disregarded
    edges_up: Edges
    edges_right: Edges

    def __init__(self, edges_up: Edges, edges_right: Edges, player_a: Player, player_b: Player):
        assert edges_up.cols == constants.BOARD_SIZE
        assert edges_up.rows == constants.BOARD_SIZE - 1  # the top-most row doesn't have a top edge

        assert edges_right.cols == constants.BOARD_SIZE - 1  # the right-most column doesn't have a right edge
        assert edges_right.rows == constants.BOARD_SIZE

        self.edges_up = edges_up
        self.edges_right = edges_right
        self.players = (player_a, player_b)

    @classmethod
    def new_game(cls):
        player_start_col = int(constants.BOARD_SIZE / 2)
        return cls(
            edges_up=Edges(constants.BOARD_SIZE - 1, constants.BOARD_SIZE),
            edges_right=Edges(constants.BOARD_SIZE, constants.BOARD_SIZE - 1),
            player_a=Player(Pos(0, player_start_col), constants.PLAYER_WALL_START_COUNT),
            player_b=Player(Pos(constants.BOARD_SIZE - 1, player_start_col), constants.PLAYER_WALL_START_COUNT),
        )

    def _wall_canonical_index(self, pos: Pos, direction: Dir) -> tuple[Pos, Dir]:
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

        # since wall operations always involve this, let's check for invalid access to walls
        if not self._is_position_inbounds(pos_canonical):
            raise IndexError("wall operation requires an invalid canonical position")
        if direction_canonical == Dir.UP and not 0 <= pos_canonical.row < constants.BOARD_SIZE - 1:
            raise IndexError(f"wall operation on top edge of row index {pos_canonical.row}")
        elif direction_canonical == Dir.RIGHT and not 0 <= pos_canonical.col < constants.BOARD_SIZE - 1:
            raise IndexError(f"wall operation on right edge of col index {pos_canonical.col}")

        return pos_canonical, direction_canonical

    def wall_exists(self, pos: Pos, direction: Dir) -> bool:
        pos, direction = self._wall_canonical_index(pos, direction)

        if direction == Dir.UP:
            return self.edges_up(pos)
        if direction == Dir.RIGHT:
            return self.edges_right(pos)

        assert False, "unreachable code"

    def wall_place(self, pos: Pos, direction: Dir) -> None:
        pos, direction = self._wall_canonical_index(pos, direction)

        if direction == Dir.UP:
            self.edges_up.set(pos)
            return
        if direction == Dir.RIGHT:
            self.edges_right.set(pos)
            return

        assert False, "unreachable code"

    def wall_place_composite(self, cell: Pos, edge: Dir, extends: Dir) -> str:
        """
        Places a 2-width wall, starting from the `edge` edge of cell `cell`, extending to `extends`.
        E.g. wall_place_composite((2, 4), Dir.UP, Dir.RIGHT) places a wall in the top edge of cells
        (2,4) and (2,5).

        This also performs checks to make sure if the moves are valid, and return a string in case
        of an error.
        """

        # note that `extends` still makes sense even after the shift
        try:
            cell_can, edge_can = self._wall_canonical_index(cell, edge)
        except IndexError:
            return f"invalid move: the cell {cell} cannot have a wall in the `{edge}` edge"

        if edge_can == Dir.UP and extends not in (Dir.LEFT, Dir.RIGHT):
            return "If placing a horizontal edge (top or bottom), the `extends` direction needs to be a horizontal direction since it's a 2-width wall"
        if edge_can == Dir.RIGHT and extends not in (Dir.UP, Dir.DOWN):
            return "If placing a vertical edge (left or right), the `extends` direction needs to be a vertical direction since it's a 2-width wall"

        cell_can_extends = cell_can + extends.as_pos_delta()
        if not self._is_position_inbounds(cell_can_extends):
            return "the `extends` direction extends to a cell that's out of the board"

        # there's no more errors, if it's edge_can == Dir.UP, the row of cell_can_extends is the
        # same as cell_can, so it's a valid row. the equivalent for Dir.RIGHT

        if self.wall_exists(cell_can, edge_can) or self.wall_exists(cell_can_extends, edge_can):
            return "the placement of this wall would overlap with an existing wall"

        # the only potential issue left is blocking, so we create a copy of the game state to place
        # the walls and perform the checks
        game_copy = copy.deepcopy(self)
        game_copy.wall_place(cell_can, edge_can)
        game_copy.wall_place(cell_can_extends, edge_can)
        if not game_copy._can_player_reach_goal(0):
            return "the placement of this wall would make it IMPOSSIBLE for player 0 to win"
        if not game_copy._can_player_reach_goal(1):
            return "the placement of this wall would make it IMPOSSIBLE for player 1 to win"

        # no more checks left, lfg
        self.wall_place(cell_can, edge_can)
        self.wall_place(cell_can_extends, edge_can)
        return ""

    def wall_placement_blocks(self, pos: Pos, direction: Dir) -> bool:
        """
        Returns whether a `wall_place(pos, direction)` would completely block the path for either
        of the players reaching the opposite edge.
        """
        pos_canonical, direction_canonical = self._wall_canonical_index(pos, direction)

        # check if wall placement is valid (not on top of another wall)
        if direction_canonical == Dir.UP and self.edges_up(pos_canonical):
            return True  # Wall already exists, can't place
        if direction_canonical == Dir.RIGHT and self.edges_right(pos_canonical):
            return True  # Wall already exists, can't place

        # let's add the wall and check if it makes it unreachable
        # NOTE: we do this against a deepcopy of self to avoid a potential error in the middle
        #       leaving a bad state upon recovery, but it's obviously super expensive to perform
        #       whenever we want to check if a wall placement would block. if it becomes a problem
        #       then i need to just do things the right way - scary stuff
        game_counterfactual = copy.deepcopy(self)
        if direction_canonical == Dir.UP:
            game_counterfactual.edges_up.set(pos_canonical)
        elif direction_canonical == Dir.RIGHT:
            game_counterfactual.edges_right.set(pos_canonical)
        else:
            assert False, "unreachable code"

        if not game_counterfactual._can_player_reach_goal(0):
            return True
        if not game_counterfactual._can_player_reach_goal(1):
            return True
        return False

    def _can_player_reach_goal(self, player_idx: int) -> bool:
        """
        Determine if the player can reach their goal row using BFS.

        Note that this disregards the opposing player's movement, so in the scenario below, it's
        considered that player 0 cannot reach their end row, even though logically its clear that
        player 1 will just sidestep to the rightmost column.

        Scenario:
            +   +   +   +
                | 1
            +   +   +   +
                |   |
            +   +   +   +
                | 0 |
            +   +   +   +
        """

        player_pos = self.players[player_idx].pos
        enemy_pos = self.players[1 - player_idx].pos
        target_row = constants.BOARD_SIZE - 1 if player_idx == 0 else 0

        queue = deque([player_pos])
        visited = {player_pos}

        while queue:
            pos = queue.popleft()

            if pos.row == target_row:
                return True

            # try all possible moves from here
            for direction in [Dir.UP, Dir.DOWN, Dir.LEFT, Dir.RIGHT]:
                new_pos = pos + direction.as_pos_delta()

                # we disregard this new position on the following conditions
                if new_pos == enemy_pos:
                    # note that this check is too conservative because while the enemy may block the
                    # path right now, it could sidestep in the future, as mentioned in the docstring
                    continue
                if not self._is_position_inbounds(new_pos):
                    continue
                if new_pos in visited:
                    continue
                if self.wall_exists(pos, direction):
                    # this check should happen after the is_position_inbounds check
                    continue

                # the new position is a valid move, so we check it
                queue.append(new_pos)
                visited.add(new_pos)

        # nothing else to look at, meaning we couldn't reach the goal
        return False

    def _is_position_inbounds(self, pos: Pos) -> bool:
        return 0 <= pos.row < constants.BOARD_SIZE and 0 <= pos.col < constants.BOARD_SIZE

    def move(self, player_idx: int, direction: Dir) -> tuple[bool, str]:
        player_pos_cur = self.players[player_idx].pos
        player_pos_new = player_pos_cur + direction.as_pos_delta()

        # check if the new position is within the board boundaries
        if not self._is_position_inbounds(player_pos_new):
            return (
                False,
                f"attempted to move from {player_pos_cur} to {player_pos_new}, but cannot move outside the board boundaries",
            )

        # check if there's a wall blocking the move
        if self.wall_exists(player_pos_cur, direction):
            return False, f"attempted to move from {player_pos_cur} to {player_pos_new}, but cannot move through a wall"

        # check player collision
        assert len(self.players) == 2, "Invalid Assumption: unexpected number of players"
        enemy_idx = 1 - player_idx  # (player_idx == 1) ? 0 : 1
        enemy_pos = self.players[enemy_idx].pos
        if player_pos_new == enemy_pos:
            return (
                False,
                f"attempted to move from {player_pos_cur} to {player_pos_new}, but cannot move to a cell already occupied by other player",
            )

        # update the player's position
        self.players[player_idx].pos = player_pos_new

        # check for win condition
        # player A wins by reaching the top row (row 8)
        if player_idx == 0 and player_pos_new.row == constants.BOARD_SIZE - 1:
            return False, ""
        # player B wins by reaching the bottom row (row 0)
        elif player_idx == 1 and player_pos_new.row == 0:
            return False, ""

        # valid move, no win
        return True, ""

    def as_str(self) -> str:
        # we return the board with the following format:
        # - each row either contains the horizontal edges or the actual cell contents
        # - the drawing is indented by 4 spaces, with the cell contents rows including its index
        #   in this indentation
        # - cells are represented by three characters, with either three spaces or the player index
        #   surrounded by spaces
        # - vertices of the board are represented by `+`, and walls are represented by | or ---
        # - below the bottom row we also include the column indexes
        #
        # example:
        #
        #     +   +   +   +   +   +   +   +   +   +
        #  8                    1
        #     +   +   +   +   +   +   +   +   +   +
        #  7
        #     +   +   +   +   +   +   +   +   +   +
        #  6
        #     +   +   +   +   +   +   +   +   +   +
        #  5
        #     +   +   +   +   +   +   +   +   +   +
        #  4
        #     +   +   +   +   +   +   +   +   +   +
        #  3
        #     +   +---+---+---+---+---+---+---+---+
        #  2          |   |   |
        #     +   +   +   +   +   +   +   +   +   +
        #  1
        #     +   +   +   +   +   +   +   +   +   +
        #  0                    0
        #     +   +   +   +   +   +   +   +   +   +
        #       0   1   2   3   4   5   6   7   8

        BOARD_SIZE = constants.BOARD_SIZE
        EMPTY_ROW_STR = "    " + "+   " * BOARD_SIZE + "+"

        # shorthand for the cell element of a given player
        player_map = {player.pos: f" {idx} " for idx, player in enumerate(self.players)}

        def save_row(row, result=list()):
            result.append(row)
            return result

        # we start from the top row, which is the highest index, and go down from there
        for row in range(BOARD_SIZE)[::-1]:
            # each iteration we print the top edge of that row followed by the cells, the bottom
            # row is written outside the loop

            # in the first (topmost) row we don't have actual edges, so we print an empty edge
            if row == BOARD_SIZE - 1:
                save_row(EMPTY_ROW_STR)
            else:
                row_str = "    "  # 4 character aligment
                for col in range(BOARD_SIZE):
                    row_str += "+"
                    row_str += "---" if self.edges_up(Pos(row, col)) else "   "
                row_str += "+"
                save_row(row_str)

            # print the walls and its cells
            cell_row_str = f"{row:2d}   "  # 4 character indentation (2 used for index) plus a space indicating the empty leftmost edge
            for col in range(BOARD_SIZE):
                pos = Pos(row, col)
                cell_row_str += player_map.get(pos, "   ")
                cell_row_str += " " if col == BOARD_SIZE - 1 or not self.edges_right(pos) else "|"
            save_row(cell_row_str)

        # bottom edge
        save_row(EMPTY_ROW_STR)
        # row coordinates
        row_coord_str = "    "
        for col in range(BOARD_SIZE):
            row_coord_str += f" {col:2d} "

        return "\n".join(save_row(row_coord_str))
