import socketio
import asyncio
from configparser import ConfigParser
from postgre import Database
from threading import Thread
from discord import TextChannel, Embed, Color, Guild, Role
from discord.ext.commands import Command
from main import Bot
import requests, json

config = ConfigParser()
config.read("config.ini")


class Comms:
    def __init__(self, bot: Bot):

        # Init socket io
        sio = socketio.AsyncClient()

        # Reply to pings
        @sio.on("ping")
        async def ping():
            await sio.emit("pong")

        @sio.on("settingsChange")
        async def settingsChange(data):
            print(data)
            if data["key"] == "bot-prefix":
                # Do stuff with data['value']
                await self.pool.execute(
                    "UPDATE guilds SET prefix = $1 WHERE guild = $2",
                    data["value"],
                    int(data["guild_id"]),
                )
                bot.prefix.update({int(data["guild_id"]): data["value"]})

        @sio.on("getAllCommands")
        async def getAllCommands(data):
            commands = []
            for command in bot.commands:
                commands.append(
                    {
                        "cog": command.cog_name,
                        "name": command.name,
                        "help": command.help,
                    }
                )
            data["commands"] = commands
            await sio.emit("allCommands", data)
            print("Performed command sync")

        @sio.on("getDisabledCommands")
        async def getDisabledCommands(data):
            disabledCommands = []
            for command in bot.disabled_command:
                disabledCommands.append({"name": command})
            data["disabledCommands"] = disabledCommands
            await sio.emit("disabledCommands", data)
            print("Performed disabled command sync")

        @sio.on("disableCommand")
        async def disableCommand(data):
            bot.disabled_command[data["name"]] = True
            await self.pool.execute(
                "INSERT INTO commands (command, disabled) VALUES ($1, $2)",
                data["name"],
                True,
            )

        @sio.on("enableCommand")
        async def enableCommand(data):
            bot.disabled_command.pop(data["name"])
            await self.pool.execute(
                "DELETE FROM commands WHERE command = $1", data["name"]
            )

        @sio.on("updateCommands")
        async def updateCommands(data):
            for command in data["enabled"]:
                is_disabled = bot.disabled_command.get(command)
                if is_disabled:
                    bot.disabled_command.pop(command)
                    await self.pool.execute(
                        "DELETE FROM commands WHERE command = $1", command
                    )
            for command in data["disabled"]:
                is_disabled = bot.disabled_command.get(command)
                if not is_disabled:
                    bot.disabled_command[command] = True
                    await self.pool.execute(
                        "INSERT INTO commands (command, disabled) VALUES ($1, $2)",
                        command,
                        True,
                    )

        @sio.on("guildEnableCommands")
        async def guildEnableCommand(data):
            guild_commands = await self.pool.fetch(
                "SELECT commands FROM guilds WHERE guild=$1", int(data["guild_id"])
            )
            if len(guild_commands) > 0:
                guild_commands = guild_commands[0].get("commands")
            else:
                await self.pool.execute(
                    "UPDATE guilds SET commands=$1 WHERE guild=$2",
                    data["commands"],
                    int(data["guild_id"]),
                )
                return
            if guild_commands != None:
                for command in data["commands"]:
                    if command in guild_commands:
                        guild_commands.remove(command)
            await self.pool.execute(
                "UPDATE guilds SET commands=$1 WHERE guild=$2",
                guild_commands,
                int(data["guild_id"]),
            )

        @sio.on("guildDisableCommands")
        async def guildDisableCommands(data):
            guild_commands = await self.pool.fetch(
                "SELECT commands FROM guilds WHERE guild=$1", int(data["guild_id"])
            )
            if len(guild_commands) > 0:
                guild_commands = guild_commands[0].get("commands")
            else:
                await self.pool.execute(
                    "UPDATE guilds SET commands=$1 WHERE guild=$2",
                    data["commands"],
                    int(data["guild_id"]),
                )
                return

            if guild_commands != None:
                for command in data["commands"]:
                    if not command in guild_commands:
                        guild_commands.append(command)
                await self.pool.execute(
                    "UPDATE guilds SET commands=$1 WHERE guild=$2",
                    guild_commands,
                    int(data["guild_id"]),
                )
            else:
                await self.pool.execute(
                    "UPDATE guilds SET commands=$1 WHERE guild=$2",
                    data["commands"],
                    int(data["guild_id"]),
                )

        @sio.on("getGuildDisabledCommands")
        async def getGuildDisabledCommands(data):
            guild_commands = await self.pool.fetch(
                "SELECT commands FROM guilds WHERE guild=$1", int(data["guild_id"])
            )
            await sio.emit(
                "sendGuildDisabledCommands",
                {
                    "sid": data["sid"],
                    "disabledCommands": guild_commands[0].get("commands"),
                },
            )

        @sio.on("embed")
        async def sendEmbed(data):
            channel: TextChannel = bot.get_channel(int(data["embed-channel"]))
            embed: Embed = bot.embed(
                description=data["message-text"],
                color=int(data["message-color"][1::], 16),
            )
            if "thumbnail" in data:
                embed.set_thumbnail(url=data["thumbnail"])
            if "image" in data:
                embed.set_image(url=data["image"])
            if "message-author-url" in data and "authorIcon" in data:
                embed.set_author(
                    name=data["message-author"],
                    url=data["message-author-url"],
                    icon_url=data["authorIcon"],
                )
            elif "message-author-url" in data:
                embed.set_author(
                    name=data["message-author"], url=data["message-author-url"]
                )
            elif "message-author" in data and "authorIcon" in data:
                embed.set_author(
                    name=data["message-author"], icon_url=data["authorIcon"]
                )
            elif "message-author" in data:
                embed.set_author(name=data["message-author"])
            asyncio.run_coroutine_threadsafe(channel.send(embed=embed), bot.loop)
        
        # @sio.on("changeCommandPerms")
        # async def changeCommandPerms(data):
        #     session = requests.Session()
        #     session.headers = {"Authorization": f'Bot {config["SECRET"]["token"]}'}
        #     commands = session.get(f'https://discord.com/api/v8/applications/{config["SECRET"]["id"]}/guilds/888111337333456916/commands')
        #     for command in commands.json():
        #         if command["name"] == "ban":
        #             commandID = command["id"]
        #             break
            
            
        #     url = f'https://discord.com/api/v8/applications/{config["SECRET"]["id"]}/guilds/888111337333456916/commands/{commandID}/permissions'
        #     json = {
        #         "permissions": [{"id": 903454770948349962, "type": 1, "permission": True}]
        #     }
        #     request = session.put(url, json=json)
        #     print(request.json())

        async def connect():
            print("running connecting method")
            await sio.connect(
                config["WEBSITE"]["url"],
                auth={"key": config["WEBSITE"]["key"]},
                transports="websocket",
            )
            await sio.wait()

        # Beginning here, this is minorly modified code from https://git.io/Jo29J
        def start_background_loop(loop: asyncio.AbstractEventLoop) -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self.loop = asyncio.new_event_loop()
        self.pool = Database(self.loop).pool
        t = Thread(target=start_background_loop, args=(self.loop,), daemon=True)
        t.start()

        task = asyncio.run_coroutine_threadsafe(connect(), self.loop)
        # End modified section
