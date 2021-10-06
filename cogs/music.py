import re

from discord.ext import commands

# Due to halted development of Lavalink, option for streaming music is still to be decided.
youtube_url = re.compile(
    r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$"
)


class Music(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        # self.bot.loop.create_task(self.__ainit__())
        self.voice_clients = {}

    # @commands.command()
    async def join(self, context: commands.Context) -> None:
        in_voice = context.author.voice
        if in_voice:
            channel = in_voice.channel

            voice_client = await channel.connect()
            self.voice_clients[context.guild.id] = voice_client

    # @commands.command()
    async def leave(self, context: commands.Context) -> None:
        voice_client = self.voice_clients.get(context.guild.id)
        if voice_client:
            await voice_client.disconnect()

        elif context.me.voice:
            await context.me.move_to(channel=None)


def setup(bot):
    bot.add_cog(Music(bot))
