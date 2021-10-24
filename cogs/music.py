import discord
from discord.ext import commands, tasks
from main import Bot
import youtube_dl
from urllib import parse
from pyppeteer import launch
import asyncio


class Music(commands.Cog):
    ydl = youtube_dl.YoutubeDL({'format': '251'})

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
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
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0')
        await page.goto(f'https://music.youtube.com/search?q={song}', {'waituntil': 'networkidle0'})
        await asyncio.sleep(0.1)
        url = await page.querySelector('yt-formatted-string[has-link-only_]:not([force-default-style]) a.yt-simple-endpoint.yt-formatted-string')
        await page.screenshot({'path': './screenshot.png', 'fullPage': True})
        url = await url.getProperty('href')
        return await url.jsonValue()
        

    @commands.command()
    async def playsong(
        self,
        context: commands.Context,
        song: str = commands.Option(None, description="The name of the song to play"),

    ) -> None:
        
        
        if context.voice_client != None:
            if context.voice_client.is_connected():
                await context.send(f'Already connected to{context.voice_client.channel}')
        else:
            await context.defer()
            url = await self.getURL(song)
            v = dict(parse.parse_qsl(parse.urlsplit(url).query))['v']
            result = self.ydl.extract_info(url=v, download=False)
            vc = await context.author.voice.channel.connect()
            vc.play(discord.FFmpegPCMAudio(result['url']))
            await context.send(f'Playing {result["title"]}')

def setup(bot: Bot):
    bot.add_cog(Music(bot))