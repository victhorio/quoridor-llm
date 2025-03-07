import json
import re

from . import aiutils, constants, quoridor


async def play(
    model: str,
    client: aiutils.AsyncOpenAI,
    tools: list[dict],
    player_plans: list[str],
    system_instructions: str,
    game: quoridor.GameState,
    player_idx: int,
    turn: int,
    history: list[str] | None = None,
) -> bool:
    messages = (
        [
            system_instructions,
            {"role": "user", "content": prompt_planning_load(game, player_idx, turn, player_plans[player_idx])},
        ]
        if not history
        else history
    )

    if not history:
        # If this is a fresh call, we need to create the updated plan
        planning_completion = await client.chat.completions.create(
            model=model,
            messages=messages,
        )

        message = planning_completion.choices[0].message
        messages.append(message)

        print(f"\n---- Player {player_idx} plan ----")
        print(message.content)
        print("----------------------------------\n")

        player_plans[player_idx] = message.content

    # Now we generate the action
    messages.append({"role": "user", "content": prompt_action_load(game, player_idx, turn, player_plans[player_idx])})
    completion = await client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="required",
    )

    message = completion.choices[0].message
    assert message.tool_calls and len(message.tool_calls) == 1
    tool_call = message.tool_calls[0]

    if tool_call.function.name == "move":
        args = json.loads(tool_call.function.arguments)
        direction = quoridor.Dir.from_str(args["direction"])
        print(f"Player {player_idx}: move({direction})")
        is_ok, err_msg = game.move(player_idx, direction)

        if not is_ok and not err_msg:
            print(f"Player {player_idx} wins!")
            return True
    elif tool_call.function.name == "place_wall":
        cell = quoridor.Pos(
            row=tool_call.function.arguments["row"],
            col=tool_call.function.arguments["col"],
        )
        edge = quoridor.Dir.from_str(tool_call.function.arguments["edge"])
        extends = quoridor.Dir.from_str(tool_call.function.arguments["extends"])
        print(f"Player {player_idx}: place_wall({cell}, {edge}, {extends})")
        err_msg = game.wall_place(cell, edge, extends)

    if err_msg:
        print(f"Error: {err_msg}")
        input("<Press enter for the agent to retry>")
        messages.extend(
            [
                message,
                aiutils.tool_result_create(tool_call, err_msg),
            ]
        )
        return await play(model, client, tools, player_plans, system_instructions, game, player_idx, turn, messages)

    return False


def prompt_action_load(game: quoridor.GameState, player_idx: int, turn: int, previous_plan: str = "") -> str:
    prompt = aiutils.prompt_read("action_phase").format(
        turn_number=turn,
        player_number=player_idx,
        target_row=0 if player_idx == 1 else constants.BOARD_SIZE - 1,
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


def prompt_planning_load(game: quoridor.GameState, player_idx: int, turn: int, previous_plan: str) -> str:
    prompt = aiutils.prompt_read("planning_phase").format(
        turn_number=turn,
        player_number=player_idx,
        target_row=0 if player_idx == 1 else constants.BOARD_SIZE - 1,
        board_representation=game.as_str(),
        player0_pos=game.players[0].pos,
        player1_pos=game.players[1].pos,
        player0_walls=game.players[0].wall_balance,
        player1_walls=game.players[1].wall_balance,
        previous_plan=previous_plan,
    )

    missing_vars = re.findall(r"\{([1-9_a-zA-Z]+)\}", prompt)
    if missing_vars:
        raise AssertionError(f"Error: Missing variables in prompt: {', '.join(missing_vars)}")

    return prompt
