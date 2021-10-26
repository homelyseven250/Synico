import discord
from discord.ext import commands, tasks
from main import Bot
import youtube_dl
from urllib import parse
from pyppeteer import launch
import asyncio
import requests


class Music(commands.Cog):
    ydl = youtube_dl.YoutubeDL({"format": "251"})

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.queues = {}
        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self) -> None:
        """
        |coro|

        An asynchronous version of :method:`__init__`
        to access coroutines.
        """
        self.browser = await launch()

    def cog_unload(self) -> None:
        """
        This method is called before the extension is unloaded
        to allow for the running task loop to gracefully
        close after finishing final iteration.
        """
        return super().cog_unload()

    async def getURL(self, song: str):
        page = await self.browser.newPage()
        await page.setUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0"
        )
        await page.goto(
            f"https://music.youtube.com/search?q={song}", {"waituntil": "networkidle0"}
        )
        url = await page.waitForXPath(
            "/html/body/ytmusic-app/ytmusic-app-layout/div[3]/ytmusic-search-page/ytmusic-tabbed-search-results-renderer/div[2]/ytmusic-section-list-renderer/div[2]/ytmusic-shelf-renderer[1]/div[2]/ytmusic-responsive-list-item-renderer/div[2]/div[1]/yt-formatted-string/a"
        )
        await page.screenshot({"path": "./screenshot.png", "fullPage": True})
        url = await url.getProperty("href")
        return await url.jsonValue()

    def playnext(self, context: commands.Context):
        if len(self.queues[context.guild.id]) > 0:
            context.voice_client.play(
                discord.FFmpegPCMAudio(self.queues[context.guild.id][0]),
                after=lambda error: self.playnext(context),
            )
            del self.queues[context.guild.id][0]

    @commands.command()
    async def stop(self, context: commands.Context) -> None:
        if context.voice_client != None:
            if context.voice_client.is_connected():
                context.voice_client.stop()
                await context.send("Stopped playing", ephemeral=True)

    @commands.command()
    async def playsong(
        self,
        context: commands.Context,
        song: str = commands.Option(None, description="The name of the song to play"),
    ) -> None:

        if (
            context.voice_client != None
            and context.voice_client.is_connected()
            and context.voice_client.channel != context.author.voice.channel
        ):
            await context.send(f"Already connected to {context.voice_client.channel}")
        else:
            await context.defer()
            url = await self.getURL(song)
            v = dict(parse.parse_qsl(parse.urlsplit(url).query))["v"]
            result = self.ydl.extract_info(url=v, download=False)
            # song = self.ydl.download([v])
            if context.voice_client != None and context.voice_client.is_connected():
                vc = context.voice_client
            else:
                vc = await context.author.voice.channel.connect()
            vc.play(
                discord.FFmpegPCMAudio(result["url"]),
                after=lambda error: self.playnext(context),
            )
            vc.source = discord.PCMVolumeTransformer(vc.source)
            await context.send(f"Playing")

    @commands.command()
    async def pause(self, context: commands.Context) -> None:
        if context.voice_client != None and context.voice_client.is_playing():

            await context.send("Paused", ephemeral=True)

    @commands.command()
    async def resume(self, context: commands.Context) -> None:
        if context.voice_client != None and context.voice_client.is_paused():
            context.voice_client.resume()
            await context.send("Resumed", ephemeral=True)

    @commands.command()
    async def volume(
        self,
        context: commands.Context,
        volume: int = commands.Option(
            None, description="The volume to set the player to"
        ),
    ) -> None:
        if context.voice_client != None and context.voice_client.is_connected():
            context.voice_client.source.volume = volume / 100
            await context.send(f"Volume set to {volume}", ephemeral=True)

    @commands.command()
    async def addtoqueue(
        self,
        context: commands.Context,
        song: str = commands.Option(None, description="Ths song to add to the queue"),
    ) -> None:
        # Check if the bot is currently playing in the guild
        await context.defer()
        if not context.guild.id in self.queues:
            self.queues[context.guild.id] = []
        url = await self.getURL(song)
        v = dict(parse.parse_qsl(parse.urlsplit(url).query))["v"]
        result = self.ydl.extract_info(url=v, download=False)
        self.queues[context.guild.id].append(result["url"])
        await context.send(
            f"Added {song} to the queue for {context.guild}", ephemeral=True
        )


def setup(bot: Bot):
    bot.add_cog(Music(bot))
