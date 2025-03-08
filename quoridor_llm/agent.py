import json
import re

from . import aiutils, constants, quoridor

TOOLS = [
    aiutils.tool_spec_create(
        name="move",
        desc="Moves orthogonally",
        params=[
            aiutils.ParamInfo(
                name="direction",
                type="string",
                desc="The direction you wish the move.",
                required=True,
                enum=["up", "down", "left", "right"],
            )
        ],
    ),
    aiutils.tool_spec_create(
        name="place_wall",
        desc="Places a 2-width wall somewhere on the board to block movement",
        params=[
            aiutils.ParamInfo(
                "row",
                type="integer",
                desc="The row (0-8) of the cell of interest",
                required=True,
            ),
            aiutils.ParamInfo(
                "col",
                type="integer",
                desc="The col (0-8) of the cell of interest",
                required=True,
            ),
            aiutils.ParamInfo(
                "edge",
                type="string",
                desc="Which edge of the row described by `(row,col)` that should receive the wall",
                required=True,
                enum=["up", "down", "left", "right"],
            ),
            aiutils.ParamInfo(
                "extends",
                type="string",
                desc="In what direction should the wall extend. For example in place_wall(2, 4, 'top', 'right') the wall will be added on the top edge of cells (2, 4) and (2, 5).",
                required=True,
                enum=["up", "down", "left", "right"],
            ),
        ],
    ),
]


async def play_turn(
    model: str,
    client: aiutils.AsyncOpenAI,
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
    messages.append({"role": "user", "content": prompt_action_load()})
    completion = await client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOLS,
        tool_choice="required",
    )

    message = completion.choices[0].message
    assert message.tool_calls and len(message.tool_calls) == 1
    tool_call = message.tool_calls[0]
    args = json.loads(tool_call.function.arguments)

    if tool_call.function.name == "move":
        direction = quoridor.Dir.from_str(args["direction"])
        print(f"Player {player_idx}: move({direction})")
        won, err_msg = game.move(player_idx, direction)
        if won:
            print(f"Player {player_idx} wins!")
            return True
    elif tool_call.function.name == "place_wall":
        cell = quoridor.Pos(row=args["row"], col=args["col"])
        edge = quoridor.Dir.from_str(args["edge"])
        extends = quoridor.Dir.from_str(args["extends"])
        print(f"Player {player_idx}: place_wall({cell}, {edge}, {extends})")
        err_msg = game.wall_place(cell, edge, extends)

    if err_msg:
        print(f"Error: {err_msg}")
        input("<Press enter for the agent to retry>")
        err_msg = f"Tool error:\n{err_msg}\n\nPlan again your next move given this information, and then I will prompt for an updated move."
        messages.extend(
            [
                message,
                aiutils.tool_result_create(tool_call, err_msg),
            ]
        )
        return await play_turn(model, client, player_plans, system_instructions, game, player_idx, turn, messages)

    return False


def prompt_planning_load(game: quoridor.GameState, player_idx: int, turn: int, previous_plan: str) -> str:
    target_row = 0 if player_idx == 1 else constants.BOARD_SIZE - 1
    target_direction = "DOWN" if player_idx == 1 else "UP"

    prompt = aiutils.prompt_read("planning_phase").format(
        turn_number=turn,
        player_number=player_idx,
        player0_pos=game.players[0].pos,
        player1_pos=game.players[1].pos,
        player0_walls=game.players[0].wall_balance,
        player1_walls=game.players[1].wall_balance,
        player_objective=f"move {target_direction} towards row {target_row}",
        wall_placements=game.edge_representations(),
        previous_plan=previous_plan,
    )

    missing_vars = re.findall(r"\{([1-9_a-zA-Z]+)\}", prompt)
    if missing_vars:
        raise AssertionError(f"Error: Missing variables in prompt: {', '.join(missing_vars)}")

    return prompt


def prompt_action_load() -> str:
    prompt = aiutils.prompt_read("action_phase")

    missing_vars = re.findall(r"\{([0-9_a-zA-Z]+)\}", prompt)
    if missing_vars:
        raise AssertionError(f"Error: Missing variables in prompt: {', '.join(missing_vars)}")

    return prompt
