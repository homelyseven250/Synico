from typing import List

import discord
from discord.ext import commands


class Developer(commands.Cog, command_attrs=dict(hidden=True, slash_command=False)):
    """
    A module to debug and give helpful information
    to developers.
    """

    def __init__(self, bot):
        self.bot = bot

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


def setup(bot):
    bot.add_cog(Developer(bot))
