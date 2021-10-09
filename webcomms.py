import socketio
import asyncio
from configparser import ConfigParser
from postgre import Database

config = ConfigParser()
config.read("config.ini")


class Comms():
    def __init__(self, bot):

        self.loop = asyncio.new_event_loop()
        self.pool = Database(self.loop).pool

        # Init socket io
        sio = socketio.Client()

        # Reply to pings
        @sio.on('ping')
        def ping():
            sio.emit('pong')

        @sio.on('settingsChange')
        def settingsChange(data):
            print(data)
            if data['key'] == 'bot-name':
                # Do stuff with data['value']
                pass

        @sio.on('getAllCommands')
        def getAllCommands(data):
            commands = []
            for command in bot.commands:
                commands.append(
                    {"cog": command.cog_name, "name": command.name, "help": command.help})
            data['commands'] = commands
            sio.emit('allCommands', data)
            print("Performed command sync")

        @sio.on('getDisabledCommands')
        def getDisabledCommands(data):
            disabledCommands = []
            for command in bot.disabled_command:
                disabledCommands.append({"name": command})
            data['disabledCommands'] = disabledCommands
            sio.emit('disabledCommands', data)
            print("Performed disabled command sync")

        @sio.on('disableCommand')
        def disableCommand(data):
            bot.disabled_command[data['name']] = True
            self.loop.run_until_complete(self.pool.execute(
                "INSERT INTO commands (command, disabled) VALUES ($1, $2)", data['name'], True))

        @sio.on('enableCommand')
        def enableCommand(data):
            bot.disabled_command.pop(data['name'])
            self.loop.run_until_complete(self.pool.execute(
                "DELETE FROM commands WHERE command = $1", data['name']))

        @sio.on('updateCommands')
        def updateCommands(data):
            for command in data['enabled']:
                is_disabled = bot.disabled_command.get(command)
                if is_disabled:
                    bot.disabled_command.pop(command)
                    self.loop.run_until_complete(self.pool.execute(
                        "DELETE FROM commands WHERE command = $1", command))
            for command in data['disabled']:
                is_disabled = bot.disabled_command.get(command)
                if not is_disabled:
                    bot.disabled_command[command] = True
                    self.loop.run_until_complete(self.pool.execute(
                        "INSERT INTO commands (command, disabled) VALUES ($1, $2)", command, True))

        # Connect to the socket io server
        sio.connect(config['WEBSITE']['url'], auth={
                    "key": config['WEBSITE']['key']})
