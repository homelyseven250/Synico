import discord
from discord.ext import commands, tasks
from main import Bot
import youtube_dl
from urllib import parse
from pyppeteer import launch


class Music(commands.Cog):
    ydl = youtube_dl.YoutubeDL({"format": "251"})

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.queues = {}
        self.currentPlaying = {}
        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self) -> None:
        """
        |coro|

        An asynchronous version of :method:`__init__`
        to access coroutines.
        """
        self.browser = await launch()

    async def getURL(self, song: str):
        # Search for the song in the database
        # If it's not found, search for it on youtube

        possibleSong = await self.bot.pool.fetchval(
            "SELECT video_id FROM music WHERE search=$1", song.lower().strip()
        )
        if possibleSong != None:
            return possibleSong
        page = await self.browser.newPage()
        await page.setUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0/2mpCQgow-36"
        )
        await page.goto(
            f"https://music.youtube.com/search?q={song}",
            {"waituntil": "domcontentloaded"},
        )
        url = await page.waitForXPath(
            "/html/body/ytmusic-app/ytmusic-app-layout/div[3]/ytmusic-search-page/ytmusic-tabbed-search-results-renderer/div[2]/ytmusic-section-list-renderer/div[2]/ytmusic-shelf-renderer[1]/div[2]/ytmusic-responsive-list-item-renderer/div[2]/div[1]/yt-formatted-string/a"
        )
        url = await url.getProperty("href")
        await self.bot.pool.execute(
            "INSERT INTO music (search, video_id) VALUES ($1, $2) ON CONFLICT (search) DO NOTHING",
            song.lower().strip(),
            await url.jsonValue(),
        )
        return await url.jsonValue()

    async def playnext(self, context: commands.Context):
        if context.guild.id in self.queues and len(self.queues[context.guild.id]) > 0:
            if self.queues[context.guild.id][0] == "loop":
                context.voice_client.play(
                    discord.FFmpegPCMAudio(
                        self.currentPlaying[context.guild.id]["url"]
                    ),
                    after=lambda e: self.bot.loop.create_task(self.playnext(context)),
                )
                return
            context.voice_client.play(
                discord.FFmpegPCMAudio(self.queues[context.guild.id][0]["url"]),
                after=lambda e: self.bot.loop.create_task(self.playnext(context)),
            )
            embed = discord.Embed(
                title="Now Playing",
                description=f"{self.queues[context.guild.id][0]['title']}",
                color=0x00FF00,
            )
            embed.set_thumbnail(
                url=f"https://img.youtube.com/vi/{self.queues[context.guild.id][0]['id']}/maxresdefault.jpg"
            )
            embed.set_footer(text=self.queues[context.guild.id][0]['channel'])
            await context.send(embed=embed)
            self.currentPlaying[context.guild.id] = self.queues[context.guild.id][0]
            del self.queues[context.guild.id][0]
        else:

            if context.voice_client != None:
                await context.voice_client.disconnect()
                embed = discord.Embed(
                    title="No more songs in queue",
                    description="",
                    color=0x00FF00,
                )
                await context.send(embed=embed)
            if context.guild.id in self.queues:
                del self.queues[context.guild.id]
            if context.guild.id in self.currentPlaying:
                del self.currentPlaying[context.guild.id]

    @commands.command()
    async def stop(self, context: commands.Context) -> None:
        if context.voice_client != None:
            if context.voice_client.is_connected():
                await context.voice_client.disconnect()
                del self.currentPlaying[context.guild.id]
                del self.queues[context.guild.id]
                embed = discord.Embed(
                    title="Stopped",
                    description="",
                    color=0x00FF00,
                )
                await context.send(embed=embed, ephemeral=True)

    @commands.command()
    async def skip(self, context: commands.Context) -> None:
        if context.voice_client != None:
            if context.voice_client.is_connected():
                context.voice_client.stop()
                await context.send("Skipped song", ephemeral=True)

    @commands.command()
    async def pause(self, context: commands.Context) -> None:
        if context.voice_client != None and context.voice_client.is_playing():
            context.voice_client.pause()
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
    async def play(
        self,
        context: commands.Context,
        song: str = commands.Option(
            None, description="The song to add to the queue, or if its empty, play now"
        ),
    ) -> None:
        # Check if the bot is currently playing in the guild
        await context.defer()
        if not context.guild.id in self.queues:
            self.queues[context.guild.id] = []
        url = await self.getURL(song)
        v = dict(parse.parse_qsl(parse.urlsplit(url).query))["v"]
        result = self.ydl.extract_info(url=v, download=False)
        self.queues[context.guild.id].append(result)
        await context.send(
            f"Added {song} to the queue for {context.guild}", ephemeral=True
        )
        if not context.guild.id in self.currentPlaying:
            if context.voice_client == None or not context.voice_client.is_connected():
                await context.author.voice.channel.connect()
            await self.playnext(context)

    @commands.group(name="loop")
    async def _loop(self, context: commands.Context) -> None:
        pass

    @_loop.command(name="song")
    async def _loop_song(self, context: commands.Context) -> None:
        if context.voice_client != None and context.voice_client.is_connected():
            if context.voice_client.is_playing():
                self.queues[context.guild.id].insert(0, "loop")
                await context.send("Looping current song", ephemeral=True)
            else:
                await context.send("Nothing is playing", ephemeral=True)

    @commands.Command
    async def queue(self, context: commands.Context) -> None:
        if context.guild.id in self.queues and len(self.queues[context.guild.id]) > 0:
            embed = discord.Embed(
                title="Queue",
                description="\n".join(
                    [
                        f"{i+1}. {song['title']}"
                        for i, song in enumerate(self.queues[context.guild.id])
                    ]
                ),
                color=0x00FF00,
            )
            await context.send(embed=embed)
        else:
            await context.send("The queue is empty.\nWhy not add a song with `/play`?", ephemeral=True)

    @commands.Command
    async def addplaylist(
        self,
        context: commands.Context,
        url: str = commands.Option(
            None, description="The playlist to add to the queue"
        ),
    ) -> None:
        await context.defer()
        if not context.guild.id in self.queues:
            self.queues[context.guild.id] = []
        result = self.ydl.extract_info(url, download=False)
        self.queues[context.guild.id] = (
            self.queues[context.guild.id] + result["entries"]
        )
        await context.send(
            f"Added {url} to the queue for {context.guild}", ephemeral=True
        )
        if not context.guild.id in self.currentPlaying:
            if context.voice_client == None or not context.voice_client.is_connected():
                await context.author.voice.channel.connect()
            await self.playnext(context)


def setup(bot: Bot):
    bot.add_cog(Music(bot))
