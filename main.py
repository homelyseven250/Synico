import asyncio
import os
from configparser import ConfigParser

import aiohttp
import discord
from discord.ext import commands

import webcomms

from postgre import Database


class Bot(commands.Bot):
    """
    A :class:`Bot` class that
    inherits from :class:`Client`.
    -----------------------------

    Attributes

    pool: :class:`Pool`
        A lingering connection pool
        established when accessing
        the database.

    uptime: :class:`datetime`
        A datetime object that is
        created when the class is initialized.

    embed: :class:`Embed`
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

    def __init__(self) -> None:

        intents = discord.Intents(
            guilds=True,
            emojis_and_stickers=True,
            invites=True,
            voice_states=True,
            guild_messages=True,
            guild_reactions=True,
        )

        super().__init__(
            command_prefix=self.get_prefix,
            case_insensitive=True,
            intents=intents,
            owner_ids=[220418804176388097, 672498629864325140, 652742251683905552],
            allowed_mentions=discord.AllowedMentions.none(),
        )

        self._BotBase__cogs = commands.core._CaseInsensitiveDict()
        self.loop = asyncio.get_event_loop()
        self.pool = Database(self.loop).pool

        self.loop.create_task(self.__ainit__())

    async def __ainit__(self) -> None:
        """
        |coro|

        An asynchronous version of :method:`__init__`
        to access coroutines.
        """
        await self.wait_until_ready()

        await self.assign_attributes()
        await self.create_caches()

    def run(self) -> None:
        """
        A method of :class:`discord.Client` that is called
        to initiate the websocket connection and
        handshake.
        """
        self.config = ConfigParser()
        self.config.read("config.ini")
        self.extensions()
        super().run(self.config["SECRET"]["token"], reconnect=True)

    async def close(self) -> None:
        """
        |coro|

        A method of :class:`discord.Client`
        called when gracefully closing
        connection with Discord.
        """
        await asyncio.wait_for(self.cs.close(), 30)
        await asyncio.wait_for(self.pool.close(), 30)
        await super().close()

    def extensions(self) -> None:
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

    def debugging(self) -> None:
        """
        A function to optionally load
        the Jishaku extension for debugging purposes.
        """
        self.load_extension("jishaku")

        os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
        os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
        os.environ["JISHAKU_HIDE"] = "True"

    async def assign_attributes(self) -> None:
        """
        |coro|

        A coroutine that assigns instance attributes
        to the class to allow for global use.
        """
        self.uptime = discord.utils.utcnow()
        self.embed = discord.Embed
        self.cs = aiohttp.ClientSession()

    async def on_ready(self) -> None:
        """
        An event fired
        once websocket connection is opened
        and handshake is successful.
        """
        print(self.user, "is now online.", round(self.latency * 1000), "ms.")

    async def on_disconnect(self) -> None:
        """
        An event fired when
        the websocket connection is interrupted
        and disconnected.
        """
        print(self.user, "has disconnected.")

    async def on_resumed(self) -> None:
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
        if message.guild and hasattr(self, "prefix"):
            if not self.prefix.get(message.guild.id, None):
                await self.add_prefix(message.guild.id)

            prefix: str = self.prefix.get(message.guild.id, self.user.mention)
            return commands.when_mentioned_or(prefix)(self, message)

    async def on_message(self, message: discord.Message):
        """
        An event fired
        when the websocket receives
        a new message.
        """
        if message.guild and not message.author.bot:
            if getattr(self, "cache", None):
                self.cache["member"].update({message.author.id: message.author})

                if self.user.mentioned_in(message):
                    self.cache["member"].update({message.author.id: message.author})

            try:
                await self.process_commands(message)
            except Exception as error:
                print(error)

    async def process_commands(self, message: discord.Message) -> None:
        context = await self.get_context(message)
        if context.command:
            command = context.command.name
            guild_commands = await self.pool.fetch('SELECT commands FROM guilds WHERE guild=$1', int(context.guild.id))
            guild_commands = guild_commands[0].get('commands')
            is_disabled = self.disabled_command.get(command)
            if guild_commands != None:
                if is_disabled or command in guild_commands:
                    await context.send(
                        f"Command `{context.prefix}{context.command.name}` is currently disabled."
                    )
                    return

            return await super().process_commands(message)

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
            "INSERT INTO guilds (guild, prefix) VALUES ($1, $2) ON CONFLICT (guild) DO NOTHING",
            guild_id,
            self.user.mention,
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
        self.cache = {"member": {}, "user": {}}

        self.prefix: dict[int, str] = {
            guild: prefix
            for guild, prefix in await self.pool.fetch(
                "SELECT guild, prefix FROM guilds"
            )
        }

        self.admins: dict[int, dict[str, int]] = {
            guild: {"admin": admin, "mod": mod}
            for guild, admin, mod in await self.pool.fetch(
                "SELECT guild, admin, mod FROM guilds"
            )
        }

        self.disabled_command: dict[str, bool] = {
            command: disabled
            for command, disabled in await self.pool.fetch(
                "SELECT command, disabled FROM commands"
            )
        }


if __name__ == "__main__":
    bot = Bot()
    socketComms = webcomms.Comms(bot)
    bot.run()
