import socketio
import asyncio
from configparser import ConfigParser
from postgre import Database
from threading import Thread

config = ConfigParser()
config.read("config.ini")


class Comms():
    def __init__(self, bot):

        

        # Init socket io
        sio = socketio.AsyncClient()

        # Reply to pings
        @sio.on('ping')
        async def ping():
            await sio.emit('pong')

        @sio.on('settingsChange')
        def settingsChange(data):
            print(data)
            if data['key'] == 'bot-name':
                # Do stuff with data['value']
                pass

        @sio.on('getAllCommands')
        async def getAllCommands(data):
            commands = []
            for command in bot.commands:
                commands.append(
                    {"cog": command.cog_name, "name": command.name, "help": command.help})
            data['commands'] = commands
            await sio.emit('allCommands', data)
            print("Performed command sync")

        @sio.on('getDisabledCommands')
        async def getDisabledCommands(data):
            disabledCommands = []
            for command in bot.disabled_command:
                disabledCommands.append({"name": command})
            data['disabledCommands'] = disabledCommands
            await sio.emit('disabledCommands', data)
            print("Performed disabled command sync")

        @sio.on('disableCommand')
        async def disableCommand(data):
            bot.disabled_command[data['name']] = True
            await self.pool.execute(
                "INSERT INTO commands (command, disabled) VALUES ($1, $2)", data['name'], True)

        @sio.on('enableCommand')
        async def enableCommand(data):
            bot.disabled_command.pop(data['name'])
            await self.pool.execute(
                "DELETE FROM commands WHERE command = $1", data['name'])

        @sio.on('updateCommands')
        async def updateCommands(data):
            for command in data['enabled']:
                is_disabled = bot.disabled_command.get(command)
                if is_disabled:
                    bot.disabled_command.pop(command)
                    await self.pool.execute(
                        "DELETE FROM commands WHERE command = $1", command)
            for command in data['disabled']:
                is_disabled = bot.disabled_command.get(command)
                if not is_disabled:
                    bot.disabled_command[command] = True
                    await self.pool.execute(
                        "INSERT INTO commands (command, disabled) VALUES ($1, $2)", command, True)

        @sio.on('guildEnableCommands')
        async def guildEnableCommand(data):
            guild_commands = await self.pool.fetch(
                'SELECT commands FROM guilds WHERE guild=$1', int(data['guild_id']))
            guild_commands = guild_commands[0].get('commands')
            for command in data['commands']:
                if command in guild_commands:
                    guild_commands.remove(command)
            await self.pool.execute(
                'UPDATE guilds SET commands=$1 WHERE guild=$2', guild_commands, int(data['guild_id']))

        @sio.on('guildDisableCommands')
        async def guildDisableCommands(data):
            guild_commands = await self.pool.fetch(
                'SELECT commands FROM guilds WHERE guild=$1', int(data['guild_id']))
            guild_commands=guild_commands[0].get('commands')
            for command in data['commands']:
                if not command in guild_commands:
                    guild_commands.append(command)
            await self.pool.execute(
                'UPDATE guilds SET commands=$1 WHERE guild=$2', guild_commands, int(data['guild_id']))

        @sio.on('getGuildDisabledCommands')
        async def getGuildDisabledCommands(data):
            guild_commands= await self.pool.fetch(
                'SELECT commands FROM guilds WHERE guild=$1', int(data['guild_id']))
            await sio.emit('sendGuildDisabledCommands', {
                     "sid": data["sid"], "disabledCommands": guild_commands[0].get('commands')})

        async def connect():
            print("running connecting method")
            await sio.connect(config['WEBSITE']['url'], auth = {
                    "key": config['WEBSITE']['key']}, transports='websocket')
            await sio.wait()
        
        #Beginning here, this is minorly modified code from https://git.io/Jo29J
        def start_background_loop(loop: asyncio.AbstractEventLoop) -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()
        

        self.loop = asyncio.new_event_loop()
        self.pool = Database(self.loop).pool
        t = Thread(target=start_background_loop, args=(self.loop,), daemon=True)
        t.start()

        task = asyncio.run_coroutine_threadsafe(connect(), self.loop)
