import pytest

from . import constants
from .quoridor import Dir, GameState, Pos


class TestQuoridorGame:
    def test_new_game(self):
        game = GameState.new_game()

        # Check initial player positions
        start_col = int(constants.BOARD_SIZE / 2)
        assert game.players[0].pos == Pos(0, start_col)  # Player A at bottom
        assert game.players[1].pos == Pos(constants.BOARD_SIZE - 1, start_col)  # Player B at top

        # Check initial wall balance
        assert game.players[0].wall_balance == constants.PLAYER_WALL_START_COUNT
        assert game.players[1].wall_balance == constants.PLAYER_WALL_START_COUNT

        # Check that no walls are placed initially for both edge types
        for row in range(constants.BOARD_SIZE - 1):
            for col in range(constants.BOARD_SIZE):
                assert not game.edges_up(Pos(row, col))

        for row in range(constants.BOARD_SIZE):
            for col in range(constants.BOARD_SIZE - 1):
                assert not game.edges_right(Pos(row, col))

    def test_move(self):
        game = GameState.new_game()
        start_col = game.players[0].pos.col

        # Player A moves up 5 times (valid)
        for i in range(5):
            won, err_msg = game.move(0, Dir.UP)
            assert not won
            assert not err_msg
            assert game.players[0].pos == Pos(1 + i, start_col)

        # Player B moves down (valid)
        won, err_msg = game.move(1, Dir.DOWN)
        assert not won
        assert not err_msg
        assert game.players[1].pos == Pos(constants.BOARD_SIZE - 2, start_col)

        # Player A moves right twice and left thrice (valid)
        for i in range(3):
            won, err_msg = game.move(0, Dir.RIGHT)
            assert not won
            assert not err_msg
            assert game.players[0].pos == Pos(5, start_col + i + 1)
        for i in range(3):
            won, err_msg = game.move(0, Dir.LEFT)
            assert not won
            assert not err_msg
        assert game.players[0].pos == Pos(5, start_col)

    def test_move_oob(self):
        game = GameState.new_game()

        # Move player A to the left edge
        for _ in range(constants.BOARD_SIZE // 2):
            game.move(0, Dir.LEFT)

        # Try to move beyond the left boundary
        won, errmsg = game.move(0, Dir.LEFT)
        assert not won
        assert "boundaries" in errmsg.lower()

        # Reset game
        game = GameState.new_game()

        # Move player B to the right edge
        for _ in range(constants.BOARD_SIZE // 2):
            game.move(1, Dir.RIGHT)

        # Try to move beyond the right boundary
        won, errmsg = game.move(1, Dir.RIGHT)
        assert not won
        assert "boundaries" in errmsg.lower()

        game = GameState.new_game()

        # Move player A below from starting position

    def test_move_into_walls(self):
        game = GameState.new_game()
        player = game.players[0]

        # Let's place walls so that if the player tries to move up once or left twice they'll
        # face an error
        game._wall_place_single(player.pos, Dir.UP)
        game._wall_place_single(player.pos + Dir.LEFT.as_pos_delta(), Dir.LEFT)

        # Try to move through the wall above
        won, errmsg = game.move(0, Dir.UP)
        assert not won
        assert "wall" in errmsg.lower()

        # Move left twice through a wall
        won, errmsg = game.move(0, Dir.LEFT)
        assert not won
        assert not errmsg
        won, errmsg = game.move(0, Dir.LEFT)
        assert not won
        assert "wall" in errmsg.lower()

    def test_move_into_player(self):
        """Test that players cannot move to the same position."""
        game = GameState.new_game()

        for _ in range(constants.BOARD_SIZE // 2):
            won, errmsg = game.move(0, Dir.UP)
            assert not won
            assert not errmsg

        for _ in range(constants.BOARD_SIZE // 2 - 1):
            won, errmsg = game.move(1, Dir.DOWN)
            assert not won
            assert not errmsg

        assert game.players[0].pos.row == game.players[1].pos.row - 1

        # Check the error both ways
        won, errmsg = game.move(1, Dir.DOWN)
        assert not won
        assert "occupied" in errmsg.lower()

        won, errmsg = game.move(0, Dir.UP)
        assert not won
        assert "occupied" in errmsg.lower()

    def test_move_into_win(self):
        """Test win conditions for both players."""
        game = GameState.new_game()

        # Move player A to the top row to win, noting that we need to sidestep the
        # other player first with a single LEFT move
        _ = game.move(0, Dir.LEFT)
        for _ in range(constants.BOARD_SIZE - 1):
            won, errmsg = game.move(0, Dir.UP)
            if _ < constants.BOARD_SIZE - 2:
                assert not won
            else:
                assert won

        # Reset game
        game = GameState.new_game()

        # Move player B to the bottom row to win
        _ = game.move(1, Dir.RIGHT)
        for _ in range(constants.BOARD_SIZE - 1):
            won, errmsg = game.move(1, Dir.DOWN)
            if _ < constants.BOARD_SIZE - 2:
                assert not won
            else:
                assert won

    def test_wall_place_single(self):
        game = GameState.new_game()

        # Place a wall
        game._wall_place_single(Pos(2, 3), Dir.DOWN)

        # Verify wall is placed two different ways
        assert game._wall_exists(Pos(2, 3), Dir.DOWN)
        assert game._wall_exists(Pos(1, 3), Dir.UP)

        with pytest.raises(AssertionError):
            game._wall_place_single(Pos(1, 3), Dir.UP)

        # test near the edges don't throw exceptions
        game = GameState.new_game()
        game._wall_place_single(Pos(constants.BOARD_SIZE - 2, 0), Dir.UP)
        game._wall_place_single(Pos(0, constants.BOARD_SIZE - 2), Dir.RIGHT)

    def test_invalid_wall_indexes_are_caught_across_api(self):
        game = GameState.new_game()

        with pytest.raises(IndexError):
            game._wall_exists(game.players[0].pos, Dir.DOWN)

        with pytest.raises(IndexError):
            game._wall_exists(game.players[1].pos, Dir.UP)

        with pytest.raises(IndexError):
            game._wall_place_single(Pos(0, 0), Dir.LEFT)

        with pytest.raises(IndexError):
            game._wall_place_single(Pos(0, constants.BOARD_SIZE - 1), Dir.RIGHT)

    def test_wall_place(self):
        """test the composite wall placement functionality."""
        game = GameState.new_game()
        N = constants.BOARD_SIZE

        result = game.wall_place(0, Pos(N - 1, 0), Dir.DOWN, Dir.RIGHT)
        assert not result
        assert game._wall_exists(Pos(N - 1, 0), Dir.DOWN)
        assert game._wall_exists(Pos(N - 1, 1), Dir.DOWN)

        result = game.wall_place(0, Pos(1, 0), Dir.RIGHT, Dir.DOWN)
        assert result == ""
        assert game._wall_exists(Pos(1, 1), Dir.LEFT)
        assert game._wall_exists(Pos(0, 1), Dir.LEFT)

    def test_wall_place_balance(self):
        """test that wall_place does correct wall balance accounting"""
        game = GameState.new_game()

        for row in range(4):
            assert not game.wall_place(0, Pos(row, 0), Dir.UP, Dir.RIGHT)
        assert game.players[0].wall_balance == 6

        for row in range(6):
            assert not game.wall_place(0, Pos(row, 2), Dir.UP, Dir.RIGHT)
        assert game.players[0].wall_balance == 0

        assert "balance" in game.wall_place(0, Pos(row, 4), Dir.UP, Dir.RIGHT)

        assert not game.wall_place(1, Pos(0, 6), Dir.UP, Dir.RIGHT)
        assert game.players[1].wall_balance == 9

    def test_wall_place_invalid_cell(self):
        """Test composite wall placement with invalid cell position."""
        game = GameState.new_game()

        # Invalid cell position (outside board boundaries)
        result = game.wall_place(0, Pos(-1, 3), Dir.UP, Dir.RIGHT)
        assert "invalid move" in result

        # Invalid cell position with wall at edge of board
        result = game.wall_place(0, Pos(constants.BOARD_SIZE - 1, 3), Dir.UP, Dir.RIGHT)
        assert "invalid move" in result

    def test_wall_place_invalid_direction(self):
        """Test composite wall placement with invalid direction combinations."""
        game = GameState.new_game()

        # Invalid direction combination for horizontal wall
        result = game.wall_place(0, Pos(3, 3), Dir.UP, Dir.UP)
        assert "horizontal direction" in result

        # Invalid direction combination for vertical wall
        result = game.wall_place(0, Pos(3, 3), Dir.RIGHT, Dir.LEFT)
        assert "vertical direction" in result

    def test_wall_place_out_of_bounds(self):
        """Test composite wall placement that would extend outside the board."""
        game = GameState.new_game()

        # Wall extending outside board horizontally
        result = game.wall_place(0, Pos(3, constants.BOARD_SIZE - 1), Dir.UP, Dir.RIGHT)
        assert "out of the board" in result or "invalid move" in result

        # Wall extending outside board vertically
        result = game.wall_place(0, Pos(constants.BOARD_SIZE - 1, 3), Dir.RIGHT, Dir.UP)
        assert "out of the board" in result or "invalid move" in result

    def test_wall_place_overlap(self):
        """Test composite wall placement that would overlap with existing walls."""
        game = GameState.new_game()

        # Place a wall first
        game._wall_place_single(Pos(4, 4), Dir.UP)

        # Try to place a composite wall that would overlap
        result = game.wall_place(0, Pos(4, 3), Dir.UP, Dir.RIGHT)
        assert "overlap" in result

    def test_wall_place_blocking(self):
        """Test composite wall placement that would block a player from reaching their goal."""
        game = GameState.new_game()

        # let's draw up the following game state manually:
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
        #     +---+---+---+---+---+---+---+---+
        #  2                                  |
        #     +   +   +   +   +   +   +   +   +   +
        #  1                                  |
        #     +   +   +   +   +   +   +   +ooo|ooo+
        #  0                    0
        #     +   +   +   +   +   +   +   +   +   +
        #       0   1   2   3   4   5   6   7   8
        # and make a final placement on (0,7)/UP/RIGHT that should block

        assert constants.BOARD_SIZE == 9, "this test is hardcoded on the board size"
        assert not game.wall_place(0, Pos(2, 0), Dir.UP, Dir.RIGHT)
        assert not game.wall_place(0, Pos(2, 2), Dir.UP, Dir.RIGHT)
        assert not game.wall_place(0, Pos(2, 4), Dir.UP, Dir.RIGHT)
        assert not game.wall_place(0, Pos(2, 6), Dir.UP, Dir.RIGHT)
        assert not game.wall_place(0, Pos(2, 7), Dir.RIGHT, Dir.DOWN)

        assert "IMPOSSIBLE" in game.wall_place(0, Pos(0, 7), Dir.UP, Dir.RIGHT)

    def test_wall_place_blocking_extra(self):
        """
        Make sure that wall_place returns an error if a placement would fully block a player.
        """

        # Case 1: Simple horizontal block
        game = GameState.new_game()

        blocked_row = 2
        for col in range(constants.BOARD_SIZE - 2):
            game._wall_place_single(Pos(blocked_row, col), Dir.UP)

        assert game._can_player_reach_goal(0)
        assert game._can_player_reach_goal(1)
        assert "IMPOSSIBLE" in game.wall_place(0, Pos(blocked_row, col + 1), Dir.UP, Dir.RIGHT)

        # Case 2: Narrow corridor. For the current implementation, this should be considered a block
        #         even if it's possible for Player 1 to sidestep the issue.
        game = GameState.new_game()
        start_col = game.players[0].pos.col

        for row in range(constants.BOARD_SIZE - 2):
            game._wall_place_single(Pos(row, start_col), Dir.LEFT)
            game._wall_place_single(Pos(row, start_col), Dir.RIGHT)

        assert game._can_player_reach_goal(0)
        assert game._can_player_reach_goal(1)
        # Fully block the left
        assert not game.wall_place(0, Pos(row + 1, start_col), Dir.LEFT, Dir.UP)
        # Now fully block the right as well
        assert "IMPOSSIBLE" in game.wall_place(0, Pos(row + 1, start_col), Dir.RIGHT, Dir.UP)

        # Case 3: Only block player 1, surrounding them with walls
        game = GameState.new_game()
        game.move(1, Dir.DOWN)
        p1_pos = game.players[1].pos
        assert not game.wall_place(0, p1_pos, Dir.UP, Dir.LEFT)
        assert not game.wall_place(0, p1_pos, Dir.LEFT, Dir.DOWN)
        assert not game.wall_place(0, p1_pos, Dir.DOWN, Dir.RIGHT)
        assert "IMPOSSIBLE" in game.wall_place(0, p1_pos, Dir.RIGHT, Dir.UP)
