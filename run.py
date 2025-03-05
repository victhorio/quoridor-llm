import asyncio

from quoridor_llm import aiutils, agent, quoridor


async def main():
    system_instructions = {"role": "system", "content": aiutils.prompt_read("system")}
    game = quoridor.GameState.new_game()
    client = aiutils.client_create()

    tools = [
        aiutils.tool_spec_create(
            "move",
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
            "place_wall",
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
        hang()
        print(game.as_str())

        for player in range(2):
            hang()
            completion = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    system_instructions,
                    {"role": "user", "content": agent.prompt_action_load(game, player, turn, player_plans[player])},
                ],
                tools=tools,
            )

            print(completion)

            hang()


if __name__ == "__main__":
    asyncio.run(main())
