import pytest

from . import constants
from .quoridor import GameState, Pos, Dir


class TestQuoridorGame:
    def test_game_initialization(self):
        """Test that a new game is initialized correctly."""
        game = GameState.new_game()

        # Check initial player positions
        start_col = int(constants.BOARD_GRID_SIZE / 2)
        assert game.players[0].pos == Pos(0, start_col)  # Player A at bottom
        assert game.players[1].pos == Pos(constants.BOARD_GRID_SIZE - 1, start_col)  # Player B at top

        # Check initial wall balance
        assert game.players[0].wall_balance == constants.PLAYER_WALL_START_COUNT
        assert game.players[1].wall_balance == constants.PLAYER_WALL_START_COUNT

        # Check that no walls are placed initially for both edge types
        for row in range(constants.BOARD_GRID_SIZE - 1):
            for col in range(constants.BOARD_GRID_SIZE):
                assert not game.edges_up(Pos(row, col))

        for row in range(constants.BOARD_GRID_SIZE):
            for col in range(constants.BOARD_GRID_SIZE - 1):
                assert not game.edges_right(Pos(row, col))

    def test_valid_moves(self):
        """Test valid player movements."""
        game = GameState.new_game()
        start_col = game.players[0].pos.col

        # Player A moves up 5 times (valid)
        for i in range(5):
            is_ok, message = game.move(0, Dir.UP)
            assert is_ok
            assert message == ""
            assert game.players[0].pos == Pos(1 + i, start_col)

        # Player B moves down (valid)
        is_ok, message = game.move(1, Dir.DOWN)
        assert is_ok
        assert message == ""
        assert game.players[1].pos == Pos(constants.BOARD_GRID_SIZE - 2, start_col)

        # Player A moves right twice and left thrice (valid)
        for i in range(3):
            is_ok, message = game.move(0, Dir.RIGHT)
            assert is_ok
            assert message == ""
            assert game.players[0].pos == Pos(5, start_col + i + 1)
        for i in range(3):
            is_ok, message = game.move(0, Dir.LEFT)
            assert is_ok
            assert message == ""
        assert game.players[0].pos == Pos(5, start_col)

    def test_invalid_moves_boundaries(self):
        """Test invalid moves due to board boundaries."""
        game = GameState.new_game()

        # Move player A to the left edge
        for _ in range(constants.BOARD_GRID_SIZE // 2):
            game.move(0, Dir.LEFT)

        # Try to move beyond the left boundary
        is_ok, message = game.move(0, Dir.LEFT)
        assert not is_ok
        assert "boundaries" in message.lower()

        # Reset game
        game = GameState.new_game()

        # Move player B to the right edge
        for _ in range(constants.BOARD_GRID_SIZE // 2):
            game.move(1, Dir.RIGHT)

        # Try to move beyond the right boundary
        is_ok, message = game.move(1, Dir.RIGHT)
        assert not is_ok
        assert "boundaries" in message.lower()

        game = GameState.new_game()

        # Move player A below from starting position

    def test_invalid_moves_walls(self):
        """Test invalid moves due to walls."""
        game = GameState.new_game()
        player = game.players[0]

        # Let's place walls so that if the player tries to move up once or left twice they'll
        # face an error
        game.wall_place(player.pos, Dir.UP)
        game.wall_place(player.pos + Dir.LEFT.as_pos_delta(), Dir.LEFT)

        # Try to move through the wall above
        is_ok, message = game.move(0, Dir.UP)
        assert not is_ok
        assert "wall" in message.lower()

        # Move left twice through a wall
        is_ok, message = game.move(0, Dir.LEFT)
        assert is_ok
        is_ok, message = game.move(0, Dir.LEFT)
        assert not is_ok
        assert "wall" in message.lower()

    def test_player_collision(self):
        """Test that players cannot move to the same position."""
        game = GameState.new_game()

        for _ in range(constants.BOARD_GRID_SIZE // 2):
            is_ok, _ = game.move(0, Dir.UP)
            assert is_ok

        for _ in range(constants.BOARD_GRID_SIZE // 2 - 1):
            is_ok, _ = game.move(1, Dir.DOWN)
            assert is_ok

        assert game.players[0].pos.row == game.players[1].pos.row - 1

        # Check the error both ways
        is_ok, message = game.move(1, Dir.DOWN)
        assert not is_ok
        assert "occupied" in message.lower()

        is_ok, message = game.move(0, Dir.UP)
        assert not is_ok
        assert "occupied" in message.lower()

    def test_win_condition(self):
        """Test win conditions for both players."""
        game = GameState.new_game()

        # Move player A to the top row to win, noting that we need to sidestep the
        # other player first with a single LEFT move
        is_ok, message = game.move(0, Dir.LEFT)
        for _ in range(constants.BOARD_GRID_SIZE - 1):
            is_ok, message = game.move(0, Dir.UP)
            if _ < constants.BOARD_GRID_SIZE - 2:
                assert is_ok
            else:
                assert not is_ok
                assert message == ""  # Empty message for win

        # Reset game
        game = GameState.new_game()

        # Move player B to the bottom row to win
        is_ok, message = game.move(1, Dir.RIGHT)
        assert is_ok
        assert message == ""
        for _ in range(constants.BOARD_GRID_SIZE - 1):
            is_ok, message = game.move(1, Dir.DOWN)
            if _ < constants.BOARD_GRID_SIZE - 2:
                assert is_ok
            else:
                assert not is_ok
                assert message == ""  # Empty message for win

    def test_wall_placement(self):
        """Test wall placement functionality."""
        game = GameState.new_game()

        # Place a wall
        game.wall_place(Pos(2, 3), Dir.DOWN)

        # Verify wall is placed two different ways
        assert game.wall_check(Pos(2, 3), Dir.DOWN)
        assert game.wall_check(Pos(1, 3), Dir.UP)

        with pytest.raises(AssertionError):
            game.wall_place(Pos(1, 3), Dir.UP)
