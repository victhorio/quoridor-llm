import asyncio

from quoridor_llm import agent, aiutils, quoridor


async def main():
    system_instructions = {"role": "system", "content": aiutils.prompt_read("system")}
    game = quoridor.GameState.new_game()
    client = aiutils.client_create()
    player_plans = ["This is the first turn, so you have not specified a plan yet."] * 2

    turn = 1
    while turn < 999:
        for player_idx in range(2):
            print(f"Player {player_idx} turn starting now")

            # this mutates the game and player_plans
            won = await agent.play_turn(
                model="gpt-4o-mini" if player_idx == 0 else "o3-mini",
                client=client,
                player_plans=player_plans,
                system_instructions=system_instructions,
                game=game,
                player_idx=player_idx,
                turn=turn,
            )

            print(game.as_str())

            if won:
                return


if __name__ == "__main__":
    asyncio.run(main())
