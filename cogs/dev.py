from typing import List

import discord

from discord.ext import commands, menus
from utils import AllCommands, SourceReader, guild_bot_owner, start_menu


class Developer(commands.Cog):
    """
    A module to debug and give helpful information
    to developers.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def source(
        self,
        context: commands.Context,
        *,
        object: SourceReader,
    ) -> None:
        """
        Display source code of a command or file.
        """
        menu = menus.MenuPages(object, delete_message_after=True)
        await menu.start(context)

    @commands.command()
    @commands.is_owner()
    async def reload(
        self,
        context: commands.Context,
        *,
        extensions: str,
    ) -> None:
        """
        Reloads selected modules.
        """
        extensions: List[str] = extensions.split()
        reloaded = []
        not_reloaded = []
        if extensions[0] == "~":
            for extension in context.bot.extensions.copy():
                try:
                    context.bot.reload_extension("cogs." + extension)
                    reloaded.append(f"🔁 | {extension}")
                except Exception as error:
                    not_reloaded.append(f"⚠️ | {extension}: {error}")

        else:
            for extension in extensions:
                try:
                    context.bot.reload_extension("cogs." + extension)
                    reloaded.append(f"🔁 | {extension}")
                except Exception as error:
                    not_reloaded.append(f"⚠️ | {extension}: {error}")

        embed: discord.Embed = context.bot.embed(
            description="\n".join(reloaded) + "\n".join(not_reloaded), color=0x006CCB
        )
        await context.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def load(self, context: commands.Context, *, extensions: str) -> None:
        """
        Loads selected modules.
        """
        extensions: List[str] = extensions.split()
        loaded = []
        not_loaded = []
        if extensions[0] == "~":
            for extension in context.bot.extensions.copy():
                try:
                    context.bot.load_extension("cogs." + extension)
                    loaded.append(f"🔁 | {extension}")
                except Exception as error:
                    not_loaded.append(f"⚠️ | {extension}: {error}")

        else:
            for extension in extensions:
                try:
                    context.bot.load_extension("cogs." + extension)
                    loaded.append(f"🔁 | {extension}")
                except Exception as error:
                    not_loaded.append(f"⚠️ | {extension}: {error}")

        embed: discord.Embed = context.bot.embed(
            description="\n".join(loaded) + "\n".join(not_loaded), color=0x006CCB
        )
        await context.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def unload(self, context: commands.Context, *, extensions: str) -> None:
        """
        Unloads selected modules.
        """
        extensions: List[str] = extensions.split()
        unloaded = []
        not_unloaded = []
        if extensions[0] == "~":
            for extension in context.bot.extensions.copy():
                try:
                    context.bot.reload_extension("cogs." + extension)
                    unloaded.append(f"🔁 | {extension}")
                except Exception as error:
                    not_unloaded.append(f"⚠️ | {extension}: {error}")

        else:
            for extension in extensions:
                try:
                    context.bot.reload_extension("cogs." + extension)
                    unloaded.append(f"🔁 | {extension}")
                except Exception as error:
                    not_unloaded.append(f"⚠️ | {extension}: {error}")

        embed: discord.Embed = context.bot.embed(
            description="\n".join(unloaded) + "\n".join(not_unloaded), color=0x006CCB
        )
        await context.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, context: commands.Context) -> None:
        """
        Shuts down bot.
        """
        time = discord.utils.utcnow()
        await context.send(
            f"{context.me} is now shutting down... {discord.utils.format_dt(time)}"
        )
        await context.bot.close()

    @commands.command()
    @commands.is_owner()
    async def disable(self, context: commands.Context, command: str) -> None:
        """
        Disables a command globally.
        """
        _command: commands.Command = context.bot.get_command(command)
        if _command:
            is_disabled: bool = context.bot.disabled_command.get(command)
            if is_disabled:
                await context.send(f"`{command}` command is already disabled.")
                return

            context.bot.disabled_command[command] = True
            await context.bot.pool.execute(
                "INSERT INTO commands (command, disabled) VALUES ($1, $2)",
                _command.name,
                True,
            )
            await context.send(f"`{command}` command has been disabled.")
            return

        await context.send(f"{command} does not exist.")

    @commands.command()
    @commands.is_owner()
    async def enable(self, context: commands.Context, command: str) -> None:
        """
        Enables a previously disabled command.
        """
        _command: commands.Command = context.bot.get_command(command)
        if _command:
            command = _command.name
            is_disabled: bool = context.bot.disabled_command.get(command)
            if not is_disabled:
                await context.send(f"{command} command is not disabled.")
                return

            context.bot.disabled_command.pop(command)
            await context.bot.pool.execute(
                "DELETE FROM commands WHERE command = $1", command
            )
            await context.send(f"`{command}` command has been enabled.")
            return

        await context.send(f"{command} does not exist.")

    @commands.command(name="commands")
    @guild_bot_owner()
    async def _commands(self, context: commands.Context):
        """
        List all commands and whether they're enabled/disabled.
        """
        all_commands: List[tuple] = []
        for command in sorted(
            [command.name.title() for command in context.bot.commands]
        ):
            is_disabled: bool = context.bot.disabled_command.get(command)
            if is_disabled:
                all_commands.append((command, is_disabled))

            else:
                all_commands.append((command, False))

        await start_menu(context, AllCommands(all_commands))


def setup(bot):
    bot.add_cog(Developer(bot))
