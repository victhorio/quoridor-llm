"""
Implementation of the actual quoridor game mechanics.
"""

import copy
from collections import deque
from dataclasses import dataclass
from enum import Enum

from . import constants


@dataclass
class Pos:
    row: int
    col: int

    def __hash__(self) -> int:
        return hash((self.row, self.col))

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
    _data: list[int]
    rows: int
    cols: int

    MASK_TOP = 0b01
    MASK_RIGHT = 0b10

    def __init__(self, rows: int, cols: int):
        self._data = [0] * rows * cols
        self.rows = rows
        self.cols = cols

    def exists(self, pos: Pos, direction: Dir) -> bool:
        """Returns whether there's a wall in direction `direction` from square `pos`."""

        if direction == Dir.DOWN:
            return self.exists(pos + Dir.DOWN.as_pos_delta(), Dir.UP)
        if direction == Dir.LEFT:
            return self.exists(pos + Dir.LEFT.as_pos_delta(), Dir.RIGHT)

        mask = self.MASK_TOP if direction == Dir.UP else self.MASK_RIGHT
        idx = pos.row * self.cols + pos.col
        return self._data[idx] & mask

    def place(self, pos: Pos, direction: Dir) -> None:
        """Sets a wall in direction `direction` from square `pos`."""

        if direction == Dir.DOWN:
            return self.place(pos + Dir.DOWN.as_pos_delta(), Dir.UP)
        if direction == Dir.LEFT:
            return self.place(pos + Dir.LEFT.as_pos_delta(), Dir.RIGHT)

        mask = self.MASK_TOP if direction == Dir.UP else self.MASK_RIGHT
        idx = pos.row * self.cols + pos.col
        self._data[idx] |= mask


class GameState:
    players: tuple[Player, Player]
    edges: Edges

    def __init__(self, edges: Edges, player_a: Player, player_b: Player):
        assert edges.cols == edges.rows
        assert edges.cols == constants.BOARD_SIZE

        self.players = (player_a, player_b)
        self.edges = edges

    @classmethod
    def new_game(cls):
        """Sets up a new clear game board"""

        player_start_col = int(constants.BOARD_SIZE / 2)
        return cls(
            edges=Edges(constants.BOARD_SIZE, constants.BOARD_SIZE),
            player_a=Player(Pos(0, player_start_col), constants.PLAYER_WALL_START_COUNT),
            player_b=Player(Pos(constants.BOARD_SIZE - 1, player_start_col), constants.PLAYER_WALL_START_COUNT),
        )

    def wall_place(self, player_idx: int, square: Pos, edge: Dir, extends: Dir) -> str:
        """
        Places a 2-width wall, starting from the `edge` edge of cell `cell`, extending to `extends`.

        E.g. wall_place_composite((2, 4), Dir.UP, Dir.RIGHT) places a wall in the top edge of cells
        (2,4) and (2,5).

        Returns a human-readable message in case of a player error.

        Note that since these are not physical walls, we DO allow for them to cross each other,
        different from the regular game.
        """

        if not self.players[player_idx].wall_balance:
            return f"player {player_idx} doesn't have any more walls left to place in balance"

        # let's do an early shift to the canonical up/right directions directly
        # note that the `extends` direction still makes sense even after the shift
        square_can, edge_can = square, edge
        if edge == Dir.DOWN:
            square_can, edge_can = square + Dir.DOWN.as_pos_delta(), Dir.UP
        elif edge == Dir.LEFT:
            square_can, edge_can = square + Dir.LEFT.as_pos_delta(), Dir.RIGHT

        # make sure the placement is in the board
        if not self._is_position_inbounds(square_can):
            return "invalid move, attempting to place a wall on the outside of the board"

        if edge_can == Dir.UP and extends not in (Dir.LEFT, Dir.RIGHT):
            return "If placing a horizontal edge (top or bottom), the `extends` direction needs to be a horizontal direction since it's a 2-width wall"
        if edge_can == Dir.RIGHT and extends not in (Dir.UP, Dir.DOWN):
            return "If placing a vertical edge (left or right), the `extends` direction needs to be a vertical direction since it's a 2-width wall"

        square_can_extends = square_can + extends.as_pos_delta()
        if not self._is_position_inbounds(square_can_extends):
            return "the `extends` direction extends to a cell that's out of the board"

        # there's no more errors, if it's edge_can == Dir.UP, the row of cell_can_extends is the
        # same as cell_can, so it's a valid row. the equivalent for Dir.RIGHT

        if self._wall_exists(square_can, edge_can) or self._wall_exists(square_can_extends, edge_can):
            return "the placement of this wall would overlap with an existing wall"

        # the only potential issue left is blocking, so we create a copy of the game state to place
        # the walls and perform the checks
        game_copy = copy.deepcopy(self)
        game_copy._wall_place_single(square_can, edge_can)
        game_copy._wall_place_single(square_can_extends, edge_can)
        if not game_copy._can_player_reach_goal(0):
            return "the placement of this wall would make it IMPOSSIBLE for player 0 to win"
        if not game_copy._can_player_reach_goal(1):
            return "the placement of this wall would make it IMPOSSIBLE for player 1 to win"

        # no more checks left, lfg
        self.players[player_idx].wall_balance -= 1
        self._wall_place_single(square_can, edge_can)
        self._wall_place_single(square_can_extends, edge_can)
        return ""

    def move(self, player_idx: int, direction: Dir) -> tuple[bool, str]:
        """
        Moves a player in a given direction.

        Returns a boolean and a string:
            - Returns True if the player won.
            - Returns a non-empty string in case of a player error with a human-readable message.
        """

        player_pos_cur = self.players[player_idx].pos
        player_pos_new = player_pos_cur + direction.as_pos_delta()

        # check if the new position is within the board boundaries
        if not self._is_position_inbounds(player_pos_new):
            return (
                False,
                f"attempted to move from {player_pos_cur} to {player_pos_new}, but cannot move outside the board boundaries",
            )

        # check if there's a wall blocking the move
        if self._wall_exists(player_pos_cur, direction):
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
            return True, ""
        # player B wins by reaching the bottom row (row 0)
        elif player_idx == 1 and player_pos_new.row == 0:
            return True, ""

        # valid move, no win
        return False, ""

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
                    row_str += "---" if self.edges.exists(Pos(row, col), Dir.UP) else "   "
                row_str += "+"
                save_row(row_str)

            # print the walls and its cells
            cell_row_str = f"{row:2d}   "  # 4 character indentation (2 used for index) plus a space indicating the empty leftmost edge
            for col in range(BOARD_SIZE):
                pos = Pos(row, col)
                cell_row_str += player_map.get(pos, "   ")
                cell_row_str += " " if col == BOARD_SIZE - 1 or not self.edges.exists(pos, Dir.RIGHT) else "|"
            save_row(cell_row_str)

        # bottom edge
        save_row(EMPTY_ROW_STR)
        # row coordinates
        row_coord_str = "    "
        for col in range(BOARD_SIZE):
            row_coord_str += f" {col:2d} "

        return "\n".join(save_row(row_coord_str))

    def edge_representations(self) -> str:
        edges = list()
        for i in range(constants.BOARD_SIZE):
            for j in range(constants.BOARD_SIZE):
                pos = Pos(i, j)
                if self.edges.exists(pos, Dir.UP):
                    edges.append([(i, j), (i + 1, j)])
                if self.edges.exists(pos, Dir.RIGHT):
                    edges.append([(i, j), (i, j + 1)])

        s = "<No walls were placed yet>"
        if edges:
            s = "\n".join(f"- wall between {e[0]} and {e[1]}" for e in edges)
        return s

    def _wall_exists(self, pos: Pos, direction: Dir) -> bool:
        return self.edges.exists(pos, direction)

    def _wall_place_single(self, pos: Pos, direction: Dir) -> None:
        return self.edges.place(pos, direction)

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
        already_tracked = {player_pos}

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
                    # of the function, but i'm satisfied with this edge case
                    continue
                if not self._is_position_inbounds(new_pos):
                    continue
                if new_pos in already_tracked:
                    continue
                if self._wall_exists(pos, direction):
                    # this check should happen after the is_position_inbounds check
                    continue

                queue.append(new_pos)
                already_tracked.add(new_pos)

        # nothing else to look at, meaning we couldn't reach the goal even after searching
        # every possible path
        return False

    def _is_position_inbounds(self, pos: Pos) -> bool:
        return 0 <= pos.row < constants.BOARD_SIZE and 0 <= pos.col < constants.BOARD_SIZE
