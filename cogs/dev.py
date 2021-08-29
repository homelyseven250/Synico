import difflib

import discord
import sphobjinv as sphinx
from discord.ext import commands
from utils import SourceReader


class Developer(commands.Cog):
    """
    A module to debug and give helpful information
    to developers.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def source(self, context, *, object: SourceReader):
        """
        Display source code of a command or file.
        """
        await object.start(context)

    @commands.command()
    @commands.is_owner()
    async def reload(self, context, *extensions):
        """
        Reloads selected modules.
        """
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

        embed = context.bot.embed(
            description="\n".join(reloaded) + "\n".join(not_reloaded), color=0x006CCB
        )
        await context.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def load(self, context, *extensions):
        """
        Loads selected modules.
        """
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

        embed = context.bot.embed(
            description="\n".join(loaded) + "\n".join(not_loaded), color=0x006CCB
        )
        await context.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def unload(self, context, *extensions):
        """
        Unloads selected modules.
        """
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

        embed = context.bot.embed(
            description="\n".join(unloaded) + "\n".join(not_unloaded), color=0x006CCB
        )
        await context.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, context: commands.Context):
        """
        Shuts down bot.
        """
        time = discord.utils.utcnow()
        await context.send(
            f"{context.me} is now shutting down... {discord.utils.format_dt(time)}"
        )
        await context.bot.close()

    def rtfm_option(self, search: str):
        """
        This method is called to access
        a dictionary to determine what type of search
        is being queried.
        """
        search = search.replace(" ", "")

        options = {
            "latest": "https://discordpy.readthedocs.io/en/latest/",
            "master": "https://discordpy.readthedocs.io/en/master/",
            "python": "https://docs.python.org/3/",
            "py": "https://docs.python.org/3/",
        }

        for key in options.keys():
            if search.startswith(key):
                return options[key], len(key)

        return options["latest"], 0

    def rtfm_matches(self, search: str):
        """
        This method handles the `.inv` file to search
        for a similar search result and return
        any close matches.
        """
        url, splice = self.rtfm_option(search.lower())

        inventory = sphinx.Inventory(url=url + "objects.inv")
        inventory_data = inventory.data_file().splitlines()

        content = []
        for _object in inventory_data[3:]:
            decoded = _object.decode("utf-8")

            obj = decoded.split(" ")[0]
            if obj == "ext/commands/api":
                break

            content.append(obj)

        similar = sorted(
            difflib.get_close_matches(search, set(content), cutoff=0.5, n=10)
        )
        if similar:
            results = {match: f"{url}api.html#" + match for match in similar}

            return results, splice + 1 if splice else splice

        return {}, 0

    @commands.command()
    async def rtfm(self, context: commands.Context, *, query: str):
        """
        Make a quick-search through the discord.py or python
        documentation.
        """
        results, splice = self.rtfm_matches(query)

        embed = context.bot.embed(
            title=f'({len(results)}) Results for "{query[splice:]}'[:255] + '"',
            description="",
            color=0x2ECC71,
        )
        for key, value in results.items():
            embed.description += f"**[`{key}`]({value})**\n"

        await context.send(embed=embed)


def setup(bot):
    bot.add_cog(Developer(bot))
