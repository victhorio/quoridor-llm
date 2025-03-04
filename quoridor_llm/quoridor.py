"""
Implementation of the actual quoridor game mechanics.
"""

from enum import Enum
from dataclasses import dataclass

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

    def wall_check(self, pos: Pos, direction: Dir) -> bool:
        if direction in (Dir.UP, Dir.DOWN):
            # this is a vertical operation, so we need to check `edges_up`
            # if the direction is down, we simply check the `up` edge of the position below
            if direction == Dir.DOWN:
                pos += Dir.DOWN.as_pos_delta()
            return self.edges_up(pos)

        if direction in (Dir.LEFT, Dir.RIGHT):
            # analogous, but for horizontal
            if direction == Dir.LEFT:
                pos += Dir.LEFT.as_pos_delta()
            return self.edges_right(pos)

        assert False, "unreachable code"

    def wall_place(self, pos: Pos, direction: Dir) -> None:
        # implementation is analogous to wall_get above
        if direction in (Dir.UP, Dir.DOWN):
            if direction == Dir.DOWN:
                pos += Dir.DOWN.as_pos_delta()
            self.edges_up.set(pos)
            return

        if direction in (Dir.LEFT, Dir.RIGHT):
            if direction == Dir.LEFT:
                pos += Dir.LEFT.as_pos_delta()
            self.edges_right.set(pos)
            return

        assert False, "unreachable code"

    def move(self, player_idx: int, direction: Dir) -> tuple[bool, str]:
        player_pos_cur = self.players[player_idx].pos
        player_pos_new = player_pos_cur + direction.as_pos_delta()

        # Check if the new position is within the board boundaries
        if not (
            0 <= player_pos_new.row < constants.BOARD_GRID_SIZE and 0 <= player_pos_new.col < constants.BOARD_GRID_SIZE
        ):
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
