import re

from . import aiutils, constants, quoridor


def prompt_action_load(game: quoridor.GameState, player_idx: int, turn: int, previous_plan: str = "") -> str:
    prompt = aiutils.prompt_read("action_phase").format(
        turn_number=turn,
        player_number=player_idx,
        target_row=0 if player_idx == 0 else constants.BOARD_SIZE - 1,
        board_representation=game.as_str(),
        player0_pos=game.players[0].pos,
        player1_pos=game.players[1].pos,
        player0_walls=game.players[0].wall_balance,
        player1_walls=game.players[1].wall_balance,
        previous_plan=previous_plan,
    )

    missing_vars = re.findall(r"\{([0-9_a-zA-Z]+)\}", prompt)
    if missing_vars:
        raise AssertionError(f"Error: Missing variables in prompt: {', '.join(missing_vars)}")

    return prompt


def prompt_planning_load(game: quoridor.GameState, player_idx: int, turn: int) -> str:
    prompt = aiutils.prompt_read("planning_phase").format(
        turn_number=turn,
        player_number=player_idx,
        player0_pos=game.players[0].pos,
        player1_pos=game.players[1].pos,
        player0_walls=game.players[0].wall_balance,
        player1_walls=game.players[1].wall_balance,
    )

    missing_vars = re.findall(r"\{([1-9_a-zA-Z]+)\}", prompt)
    if missing_vars:
        raise AssertionError(f"Error: Missing variables in prompt: {', '.join(missing_vars)}")

    return prompt
