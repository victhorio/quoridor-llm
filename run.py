import asyncio
import json

from quoridor_llm import aiutils, agent, quoridor


async def main():
    system_instructions = {"role": "system", "content": aiutils.prompt_read("system")}
    game = quoridor.GameState.new_game()
    client = aiutils.client_create()

    tools = [
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

    player_plans = ["This is the first turn, so you have not specified a plan yet."] * 2

    hang = lambda: input("<Press enter to continue>")

    turn = 1
    while turn < 999:
        for player in range(2):
            print(f"Player {player} turn starting now")

            # this mutates the game and player_plans
            is_over = await agent.play(
                model="gpt-4o-mini" if player == 0 else "gpt-4o",
                client=client,
                tools=tools,
                player_plans=player_plans,
                system_instructions=system_instructions,
                game=game,
                player_idx=player,
                turn=turn,
            )

            print(game.as_str())

            if is_over:
                return

            hang()


if __name__ == "__main__":
    asyncio.run(main())
