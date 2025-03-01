"""
Implementation of the actual quoridor game mechanics.
"""

from enum import Enum
from typing import NamedTuple

from . import constants


class Pos(NamedTuple):
    row: int
    col: int


class Player(NamedTuple):
    pos: Pos
    wall_balance: int


class Dir(Enum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3

    def as_delta(self) -> tuple[int, int]:
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

    def __call__(self, row: int, col: int) -> bool:
        return self._cells[row * self.cols + col]

    def set(self, row: int, col: int) -> None:
        idx = row * self.cols + col
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
        assert edges_up.cols == constants.BOARD_SIZE
        assert edges_up.rows == constants.BOARD_SIZE - 1

        assert edges_right.cols == constants.BOARD_SIZE - 1
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
            player_a=Player(Pos(0, player_start_col), constants.PLAYER_WALL_BALANCE_START),
            player_b=Player(Pos(constants.BOARD_SIZE - 1, player_start_col), constants.PLAYER_WALL_BALANCE_START),
        )

    def cell_get(self, row: int, col: int) -> str:
        for i, player in enumerate(self.players):
            if player.pos == (row, col):
                return chr(ord("A") + i)
        return ""

    def wall_get(self, row: int, col: int, direction: Dir) -> bool:
        if direction in (Dir.UP, Dir.DOWN):
            # This is a `row` wall operation. If we're referring to the bottom edge it's just the
            # top edge of the bottom cell.
            if direction == Dir.DOWN:
                row -= 1
            return self.edges_up(row, col)

        if direction in (Dir.LEFT, Dir.RIGHT):
            # Analogous.
            if direction == Dir.LEFT:
                col -= 1
            return self.edges_right(row, col)

    def wall_place(self, row: int, col: int, direction: Dir) -> None:
        if direction in (Dir.UP, Dir.DOWN):
            # This is a `row` wall operation. If we're referring to the bottom edge it's just the
            # top edge of the bottom cell.
            if direction == Dir.DOWN:
                row -= 1
            self.edges_up.set(row, col)
        elif direction in (Dir.LEFT, Dir.RIGHT):
            # Analogous.
            if direction == Dir.LEFT:
                col -= 1
            self.edges_right.set(row, col)

    def move(self, player: str, direction: Dir) -> tuple[bool, str]:
        player_idx = ord(player) - ord("A")
        player_pos_curr = self.players[player_idx].pos
        direction_delta = direction.as_delta()
        player_pos_new = Pos(player_pos_curr.row + direction_delta.row, player_pos_curr.col + direction_delta.col)

        # Check if the new position is within the board boundaries
        if not (0 <= player_pos_new.row < constants.BOARD_SIZE and 0 <= player_pos_new.col < constants.BOARD_SIZE):
            return False, "Cannot move outside the board boundaries"

        # Check if there's a wall blocking the move
        if self.wall_get(player_pos_curr.row, player_pos_curr.col, direction):
            return False, "Cannot move through a wall"

        # Check player collision
        assert len(self.players) == 2
        enemy_idx = 1 - player_idx  # (player_idx == 1) ? 0 : 1
        enemy_pos = self.players[enemy_idx].pos
        if player_pos_new == enemy_pos:
            return False, "Tried to move to a cell already occupied by other player"

        # Update the player's position
        self.players = (
            Player(player_pos_new, self.players[0].wall_balance) if player_idx == 0 else self.players[0],
            Player(player_pos_new, self.players[1].wall_balance) if player_idx == 1 else self.players[1],
        )

        # Check for win condition
        # Player A wins by reaching the top row (row 8)
        if player_idx == 0 and player_pos_new.row == constants.BOARD_SIZE - 1:
            return False, ""
        # Player B wins by reaching the bottom row (row 0)
        elif player_idx == 1 and player_pos_new.row == 0:
            return False, ""

        # Valid move, no win
        return True, ""
