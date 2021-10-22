import asyncio
from typing import List, Union
import discord
import random

from discord import interactions
from main import Bot
from discord.ext import commands


class Games(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(name="play")
    async def _play(self, context: commands.Context):
        pass

    @_play.command()
    async def rps(
        self,
        context: commands.Context,
        player_2: discord.Member = commands.Option(
            None, description="Choose a member to play against."
        ),
    ):
        """
        Play a game of Rock, Paper, Scissors against another member or AI.
        """
        options = (
            ("🪨", "rock"),
            ("📰", "paper"),
            ("✂️", "scissors"),
            ("🏳️", "to surrender"),
        )

        choice = {
            "rock": "paper",
            "paper": "scissors",
            "scissors": "rock",
            "surrender": None,
        }
        player_1 = context.author
        player_2 = player_2 or context.me

        if player_2.id == player_1.id or (player_2.bot and not context.me):
            return await context.send(
                f"You cannot play against {player_2}.", ephemeral=True
            )

        players = [player_1.id, player_2.id]
        view = discord.ui.View(timeout=60)
        for emoji, _id in options:
            button = discord.ui.Button(emoji=emoji, custom_id=_id)
            view.add_item(button)

        embed: discord.Embed = self.bot.embed(
            title=f"{player_1} Vs. {player_2 or context.me}"[:256], color=0x2ECC71
        )
        embed.set_footer(
            text="Rock, Paper, Scissors or surrender\nSelect an option below."
        )
        message: discord.Message = await context.send(embed=embed, view=view)
        if player_2.id == context.me.id:
            player_2_choice = random.choice(
                [option for _, option in options if option != "to surrender"]
            )
            try:
                interaction: discord.Interaction = await self.bot.wait_for(
                    "interaction",
                    check=lambda i: i.message.id == message.id
                    and i.user.id == player_1.id,
                )

                player_1_choice = interaction.data.get("custom_id")
                winner = (
                    player_2
                    if "surrender" in player_1_choice
                    else player_1
                    if player_1_choice == choice[player_2_choice]
                    else player_2
                    if player_1_choice != player_2_choice
                    else None
                )
                embed.description = (
                    f"```diff\n+ {player_1} chose {player_1_choice}\n"
                    f"+ {player_2} chose {player_2_choice}\n"
                    f"{'-' if winner else '+'} {winner or player_1} {'wins' if winner else f'tied with {player_2}'}\n```"
                )
                embed.remove_footer()
                await message.edit(embed=embed, view=None)
                return
            except asyncio.TimeoutError:
                embed.description = (
                    f"```diff\n+ {player_1} did not choose.\n"
                    f"- {player_2} wins.\n```"
                )
                embed.remove_footer()
                await message.edit(embed=embed, view=None)

        player_1_choice = None
        player_2_choice = None
        for _ in range(len(players)):
            try:
                interaction: discord.Interaction = await self.bot.wait_for(
                    "interaction",
                    check=lambda i: i.message.id == message.id and i.user.id in players,
                    timeout=120,
                )

                if interaction.user.id == player_1.id:
                    player_1_choice: str = interaction.data.get("custom_id")

                elif interaction.user.id == player_2.id:
                    player_2_choice: str = interaction.data.get("custom_id")

                embed.title = (
                    f"{player_1} has chosen. Waiting for {player_2}."
                    if player_1_choice and not player_2_choice
                    else f"{player_2} has chosen. Waiting for {player_1}."
                    if player_2_choice and not player_1_choice
                    else embed.title
                    if not player_1_choice and not player_2_choice
                    else f"{player_1} and {player_2} locked in."
                )
                await message.edit(embed=embed)
            except asyncio.TimeoutError:
                embed.title = (
                    f"{player_1} wins. {player_2} did not choose."
                    if player_1_choice and not player_2_choice
                    else f"{player_2} wins. {player_1} did not choose."
                    if player_2_choice and not player_1_choice
                    else f"{player_1} and {player_1} did not choose."
                )
                await message.edit(embed=embed)
                return

        await asyncio.sleep(2)

        winner = (
            player_2
            if "surrender" in player_1_choice
            else player_1
            if player_1_choice == choice[player_2_choice]
            else player_2
            if player_1_choice != player_2_choice
            else None
        )
        embed.description = (
            f"```diff\n+ {player_1} chose {player_1_choice}\n"
            f"+ {player_2} chose {player_2_choice}\n"
            f"{'-' if winner else '+'} {winner or player_1} {'wins' if winner else f'tied with {player_2}'}\n```"
        )
        embed.remove_footer()
        await message.edit(embed=embed, view=None)

    @_play.command()
    async def slots(self, context: commands.Context):

        view = discord.ui.View()
        static_emotes = ["🍒", "🍇", "🍋", "🍉", "⭐", "🍒", "🍇", "🍋", "🍉"]
        final_row = [
            discord.ui.Button(emoji="➡️", row=3),
            discord.ui.Button(custom_id="spin", emoji="🕹️", row=3),
            discord.ui.Button(emoji="⬅️", row=3),
        ]

        for button in [
            discord.ui.Button(
                emoji=random.choice(static_emotes),
                row=0 if row < 3 else 1 if 6 >= row > 3 else 2,
            )
            for row in range(len(static_emotes))
        ]:
            view.add_item(button)

        for button in final_row:
            view.add_item(button)

        async def spinning() -> List[discord.ui.Button]:
            view.clear_items()
            for button in [
                discord.ui.Button(
                    emoji=self.bot.get_emoji(emoji),
                    row=0 if row < 3 else 1 if 6 >= row > 3 else 2,
                )
                for row, emoji in enumerate(
                    [
                        900262456205660183,
                        900262456453107732,
                        900262456499253340,
                        900262456453107732,
                        900262456205660183,
                        900262456499253340,
                        900262456499253340,
                        900262456453107732,
                        900262456205660183,
                    ]
                )
            ]:
                view.add_item(button)

            for button in final_row:
                button.disabled = True
                view.add_item(button)

            await message.edit("\u200b", view=view)
            await asyncio.sleep(3)
            return stop()

        def stop() -> List[discord.ui.Button]:
            view.clear_items()
            new_row = [
                discord.ui.Button(
                    emoji=random.choice(static_emotes),
                    row=0 if index <= 3 else 1 if 6 >= index > 3 else 2,
                    custom_id=str(index),
                )
                for index, _ in enumerate(static_emotes, start=1)
            ]
            for button in new_row:
                view.add_item(button)

            for button in final_row:
                view.add_item(button)

            new_row_dict = {button.custom_id: button.emoji.name for button in new_row}
            return new_row_dict

        def is_winner(check_against_dict: dict) -> bool:
            win_conditions = [
                (1, 2, 3),
                (4, 5, 6),
                (7, 8, 9),
                (1, 4, 7),
                (2, 5, 8),
                (3, 6, 9),
                (1, 5, 9),
                (3, 5, 7),
            ]

            condition_check = []
            for a, b, c in win_conditions:
                condition_check.append(
                    (
                        check_against_dict[str(a)],
                        check_against_dict[str(b)],
                        check_against_dict[str(c)],
                    )
                )

            for x, y, z in condition_check:
                if x == y == z:
                    return True

            return False

        message: discord.Message = await context.send("\u200b", view=view)

        async def restart():
            updated_buttons = [button for button in view.children[:-3] if button] + [
                discord.ui.Button(custom_id="restart", emoji="🔁", row=3),
                discord.ui.Button(emoji="↔️", row=3),
                discord.ui.Button(
                    emoji="⏹️",
                    row=3,
                    custom_id="finish",
                ),
            ]
            view.clear_items()
            for item in updated_buttons:
                view.add_item(item)

            await message.edit(
                content=f"```diff\n{'+' if won else '-'} You {'win' if won is True else 'lose'}!```",
                view=view,
            )

            try:
                interaction: discord.Interaction = await self.bot.wait_for(
                    "interaction",
                    check=lambda i: i.message.id == message.id
                    and i.user.id == context.author.id
                    and i.data.get("custom_id") in ("restart", "finish"),
                    timeout=60,
                )

                if interaction.data.get("custom_id") == "finish":
                    for button in view.children:
                        if isinstance(button, discord.ui.Button):
                            button.disabled = True

                    await message.edit(view=view)

                elif interaction.data.get("custom_id") == "restart":
                    await context.command.invoke(context)

            except asyncio.TimeoutError:
                for button in view.children:
                    if isinstance(button, discord.ui.Button):
                        button.disabled = True

                await message.edit(view=view)

        try:
            _: discord.Interaction = await self.bot.wait_for(
                "interaction",
                timeout=60,
                check=lambda i: i.message.id == message.id
                and i.user.id == context.author.id
                and i.data.get("custom_id") == "spin",
            )

            results_dict = await spinning()
            won = is_winner(results_dict)
            await restart()
        except asyncio.TimeoutError:
            for button in view.children:
                if isinstance(button, discord.ui.Button):
                    button.disabled = True

            await message.edit(content="Timed out.", view=view)


def setup(bot: Bot):
    bot.add_cog(Games(bot))
