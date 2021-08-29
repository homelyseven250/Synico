import asyncio
import os
from configparser import ConfigParser

import aiohttp
import discord
from discord.ext import commands

from postgre import database


class Bot(commands.Bot):
    """
    A :class:`Bot` class that
    inherits from :class:`Client`.
    -----------------------------
    Creates a Bot instance when
    the class is initialized.

    Attributes
    ----------
    pool: :class:`asyncpg.pool.Pool`
        A lingering connection pool
        established when accessing
        the database.

    uptime: :class:`datetime`
        A datetime object that is
        created when the class is initialized.

    embed: :class:`discord.Embed`
        An Embed that has not been
        initialized to avoid calling multiple
        times unneedingly and accepts the
        usual `*args` and `**kwargs`.

    config: :class:`ConfigParser`
        A ConfigParser object to allow
        global access to the config file.

    cs: :class:`ClientSession`
        A :class:`aiohttp.ClientSession` connection
        opened on initialization to allow for
        continued use without having to open and
        close connections.
    """

    def __init__(self):

        super().__init__(
            command_prefix=self.get_prefix,
            case_insensitive=True,
            help_command=None,
            intents=discord.Intents.default(),
            owner_ids=[220418804176388097, 672498629864325140],
            allowed_mentions=discord.AllowedMentions.none(),
        )

        self._BotBase__cogs = commands.core._CaseInsensitiveDict()
        self.loop = asyncio.get_event_loop()
        self.pool = database(self.loop).pool

        self.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        """
        |coro|

        An asynchronous version of :method:`__init__`
        to access coroutines.
        """
        await self.wait_until_ready()

        await self.assign_attributes()
        await self.create_caches()

        self.all_extensions()

    def run(self):
        """
        A method of :class:`discord.Client` that is called
        to initiate the websocket connection and
        handshake.
        """
        self.config = ConfigParser()
        self.config.read("config.ini")
        super().run(self.config["SECRET"]["token"], reconnect=True)

    async def close(self):
        """
        |coro|

        A method of :class:`discord.Client`
        called when gracefully closing
        connection with Discord.
        """
        await asyncio.wait_for(self.cs.close(), 30)
        await asyncio.wait_for(self.pool.close(), 30)
        await super().close()

    def all_extensions(self):
        """
        This will iterate through the files present in
        the folder named 'cogs' and register them as extensions.
        """
        for cog in os.listdir("./cogs"):
            if cog.endswith(".py"):
                try:
                    self.load_extension(f"cogs.{cog[:-3]}")
                except Exception as error:
                    print(f"Could not load [{cog}]: {error}")

        if bool(self.config["SETTINGS"]["debug"]):
            self.debugging()

    def debugging(self):
        """
        A function to optionally load
        the Jishaku extension for debugging purposes.
        """
        self.load_extension("jishaku")

        os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
        os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
        os.environ["JISHAKU_HIDE"] = "True"

    async def assign_attributes(self):
        """
        |coro|

        A coroutine that assigns instance attributes
        to the class to allow for global use.
        """
        self.uptime = discord.utils.utcnow()
        self.embed = discord.Embed
        self.cs = aiohttp.ClientSession()

    async def on_ready(self):
        """
        An event fired
        once websocket connection is opened
        and handshake is successful.
        """
        print(self.user, "is now online.", round(self.latency * 1000), "ms.")

    async def on_disconnect(self):
        """
        An event fired when
        the websocket connection is interrupted
        and disconnected.
        """
        print(self.user, "has disconnected.")

    async def on_resumed(self):
        """
        An event fired once the websocket
        connection is reestablished.
        """
        self.uptime = discord.utils.utcnow()
        print(self.user, "has reconnected.", round(self.latency * 1000), "ms.")

    async def get_prefix(self, message: discord.Message):
        """
        |coro|

        returns :class:`str` containing the prefix set for the :class:`discord.Guild`
        or defaults to default prefix.
        """
        if message.guild:
            if not self.prefix.get(message.guild.id, None):
                await self.add_prefix(message.guild.id)

            prefix = self.prefix.get(message.guild.id)
            return commands.when_mentioned_or(prefix)(self, message)

    async def on_message(self, message: discord.Message):
        """
        An event fired
        when the websocket receives
        a new message.
        """
        if message.guild and not message.author.bot:
            if getattr(self, "cache"):
                self.cache["member"].update(
                    {message.author.id: message.author}
                )  # Pre-message intent local caching

                if self.user.mentioned_in(message):
                    self.cache["member"].update(
                        {message.author.id: message.author}
                    )  # Post-message intent local caching

            try:
                await self.process_commands(message)
            except Exception as error:
                print(error)

    async def on_command_completion(self, context: commands.Context):
        """
        An event fired when a command has
        been invoked successfully.
        """
        self.cache["member"].update({context.author.id: context.author})

    async def add_prefix(self, guild_id: int):
        """
        |coro|

        Updates local cache and database with the :class:`str` of
        the prefix assign to the :class:`discord.Guild`.
        """
        await self.pool.execute(
            "INSERT INTO guild VALUES ($1, $2, $3) ON CONFLICT (guild_id) DO NOTHING",
            guild_id,
            self.user.mention,
            False,
        )

        self.prefix.update({guild_id: self.user.mention})
        return self.user.mention

    async def create_caches(self):
        """
        |coro|

        Similar to :method:`assign_attributes`, this method
        will assign instance attributes that specifically build
        the local cache after accessing the database.
        """
        self.cache = {"member": {}}

        self.prefix = {
            guild: prefix
            for guild, prefix in await self.pool.fetch(
                "SELECT guild_id, prefix FROM guild"
            )
        }

        self.admins = {
            guild: {"admin": admin, "mod": mod}
            for guild, admin, mod in await self.pool.fetch(
                "SELECT guild_id, admin, mod FROM guild"
            )
        }


if __name__ == "__main__":
    bot = Bot()
    bot.run()
