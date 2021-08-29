import asyncio
from io import BytesIO
from typing import Optional

import discord
from bs4 import BeautifulSoup
from discord.ext import commands, tasks
from pyppeteer import launch
from utils import Streamers, is_mod, start_menu


class Streams(commands.Cog):
    """
    A module dedicated to Twitch Live notifications.
    """

    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.__ainit__())

    def cog_unload(self):
        """
        This method is called before the extension is unloaded
        to allow for the running task loop to gracefully
        close after finishing final iteration.
        """
        self.twitch_live.stop()
        return super().cog_unload()

    async def __ainit__(self):
        """
        |coro|

        An asynchronous version of :method:`__init__`
        to access coroutines.
        """
        self.twitch_live.start()

    @tasks.loop(seconds=30, reconnect=True)
    async def twitch_live(self):
        """
        |coro|

        A running task loop that repeats after each iteration
        asynchronously to check the status of Twitch streamers.
        """
        still_live = self.is_live.copy()
        for guild in self.bot.guilds:
            for streamer in still_live.keys():

                guild_exists = self.is_live[streamer].get(guild.id, None)
                if not guild_exists:
                    continue

                channel = self.bot.get_channel(
                    self.is_live[streamer][guild.id].get("channel")
                )
                if not channel:
                    continue

                await self.page.goto("https://www.twitch.tv/" + streamer)
                await asyncio.sleep(3)

                content = await self.page.content()
                soup = BeautifulSoup(content, "html.parser")
                is_live = bool("LIVE" in [s.text for s in soup.find_all("p")])

                title = [s.text for s in soup.find_all("h2")]
                if title:
                    title = title[0]

                if (
                    not title
                    or (
                        title == self.is_live[streamer].get("title")
                        and self.is_live[streamer].get("live")
                    )
                    or self.is_live[streamer][guild.id].get("notified")
                ):
                    continue

                mature_stream = [
                    s
                    for s in soup.find_all("button")
                    if s.get("data-a-target") == "player-overlay-mature-accept"
                ]

                if mature_stream:
                    button = await self.page.xpath("//*[text() = 'Start Watching']")

                    if button:
                        await button[0].click()
                        await asyncio.sleep(3)

                if not is_live:
                    self.is_live[streamer].update({"live": False})
                    self.is_live[streamer][guild.id].update({"notified": False})

                    await self.bot.pool.execute(
                        "UPDATE streams SET guild_notified = $1", True
                    )
                    await self.bot.pool.execute(
                        "UPDATE streams SET still_live = $1", True
                    )

                    continue

                stream_uptime = [
                    s.text for s in soup.find_all("span", class_="live-time")
                ]
                if not stream_uptime:
                    continue

                for _ in range(6):
                    twitch_ad = [
                        s.text
                        for s in soup.find_all("div")
                        if s.get("data-a-target") == "video-ad-countdown"
                    ]
                    if twitch_ad:
                        ad = twitch_ad[0].split(":")
                        try:
                            ad_countdown = (int(ad[0]) * 60) + int(ad[1])
                            await asyncio.sleep(ad_countdown)
                        except ValueError:
                            await asyncio.sleep(30)
                            await self.page.reload()
                    else:
                        break

                try:
                    game = [
                        s.text
                        for s in soup.find_all("a")
                        if s.get("data-a-target") == "stream-game-link"
                    ][0]

                    viewers = [
                        s.text
                        for s in soup.find_all("p")
                        if s.get("data-a-target") == "animated-channel-viewers-count"
                    ][0]

                    streamer_avatar = [
                        s.get("src")
                        for s in soup.find_all("img")
                        if str(s.get("alt")).lower() == streamer
                    ][0]

                    await self.page.mouse.click(x=1920, y=1080)
                    await asyncio.sleep(10)

                    fp = BytesIO(
                        await self.page.screenshot(
                            options={
                                "type": "jpeg",
                                "clip": {
                                    "x": 50,
                                    "y": 50,
                                    "width": 750,
                                    "height": 420,
                                },
                            }
                        )
                    )
                    fp.seek(0)

                    file = discord.File(fp=fp, filename="preview.png")

                    embed = self.bot.embed(
                        description=f"[{title}](https://www.twitch.tv/{streamer})",
                        color=0x2ECC71,
                    )
                    embed.set_author(
                        name=f"{streamer}",
                        url=f"https://www.twitch.tv/{streamer}",
                        icon_url=streamer_avatar,
                    )
                    embed.set_thumbnail(url=streamer_avatar)
                    embed.set_image(url="attachment://preview.png")

                    embed.add_field(name="Game", value=game)
                    embed.add_field(name="Viewers", value=viewers)
                    embed.add_field(name="Uptime", value=stream_uptime[0])

                    self.is_live.get(streamer).update({"live": True})
                    self.is_live.get(streamer).get(guild.id).update({"notified": True})

                    await self.bot.pool.execute(
                        "UPDATE streams SET guild_notified = $1",
                        True,
                    )
                    await self.bot.pool.execute(
                        "UPDATE streams SET still_live = $1", True
                    )

                    self.is_live.get(streamer).update({"title": title})
                    await self.bot.pool.execute(
                        "UPDATE streams SET stream_title = $1",
                        title,
                    )

                    await channel.send(
                        content=still_live[streamer].get(guild.id).get("message"),
                        embed=embed,
                        file=file,
                        allowed_mentions=discord.AllowedMentions.all(),
                    )
                    continue

                except IndexError:
                    continue

    @twitch_live.before_loop
    async def before_twitch_live(self):
        """
        |coro|

        This method is called before the main task loop
        is called to ensure instance attributes are
        assigned.
        """
        self.bot.browser = await launch(
            options={
                "executablePath": "C:\Program Files\Google\Chrome\Application\chrome.exe",
                "headless": True,
            }
        )

        pages = await self.bot.browser.pages()
        self.page = pages[0]

        self.is_live = {
            streamer: {
                "live": live,
                guild: {
                    "channel": channel,
                    "message": custom_message,
                    "notified": notified,
                },
                "title": stream_title,
            }
            for streamer, live, guild, channel, custom_message, stream_title, notified in await self.bot.pool.fetch(
                "SELECT streamer, still_live, guild, live_channel, custom_message, stream_title, guild_notified FROM streams"
            )
        }

    @commands.group(invoke_without_command=True)
    @is_mod()
    async def twitch(self, context: commands.Context):
        """
        Show currently followed Twitch channels.
        """
        streamers = await context.bot.pool.fetch(
            "SELECT streamer FROM streams WHERE guild = $1", context.guild.id
        )

        if streamers:
            await start_menu(context, Streamers(streamers))

        else:
            await context.send(f"No Twitch channels are followed in {context.guild}")

    @twitch.command(name="follow")
    @is_mod()
    async def twitch_follow(
        self,
        context: commands.Context,
        streamer: str,
        channel: Optional[discord.TextChannel] = None,
        *,
        announcement: str = None,
    ):
        """
        Follow a Twitch channel to be notified
        when they go live.
        """
        channel = channel or context.channel

        if streamer.lower().__contains__("twitch.tv/"):
            streamer = streamer.lower().split("twitch.tv/")[1]

        stream_cached = self.is_live.get(streamer.lower())

        if stream_cached:
            self.is_live[streamer.lower()].update(
                {
                    "live": stream_cached["live"],
                    "title": "",
                    context.guild.id: {
                        "channel": channel.id,
                        "message": announcement,
                        "notified": False,
                    },
                }
            )

        else:
            self.is_live.update(
                {
                    streamer.lower(): {
                        "live": False,
                        "title": "",
                        context.guild.id: {
                            "channel": channel.id,
                            "message": announcement,
                            "notified": False,
                        },
                    }
                }
            )

        await context.bot.pool.execute(
            "INSERT INTO streams VALUES ($1, $2, $3, $4, $5)",
            context.guild.id,
            channel.id,
            streamer.lower(),
            False,
            announcement
            or f"{streamer.title()} is now live at https://www.twitch.tv/{streamer.lower()}",
        )

        await context.send(
            f"{context.guild} is now following <https://www.twitch.tv/{streamer.lower()}>"
        )

    @twitch.command(name="unfollow")
    @is_mod()
    async def twitch_unfollow(self, context: commands.Context, *, streamer: str):
        """
        Unfollow a Twitch channel and no longer get notified
        when they go live.
        """
        stream = self.is_live.get(streamer.lower(), None)
        if stream:
            guild_exists = self.is_live.get(streamer.lower()).get(
                context.guild.id, None
            )
            if guild_exists:
                self.is_live.get(streamer.lower()).pop(context.guild.id)
                await context.bot.pool.execute(
                    "DELETE FROM streams WHERE guild = $1 AND streamer = $2",
                    context.guild.id,
                    streamer.lower(),
                )
                await context.send(
                    f"{context.guild} unfollowed <https://www.twitch.tv/{streamer.lower()}>"
                )

            else:
                await context.send(
                    f"{context.guild} does not follow <https://www.twitch.tv/{streamer.lower()}>"
                )

        elif not stream:
            await context.send(
                f"{context.guild} is not following <https://www.twitch.tv/{streamer.lower()}>"
            )


def setup(bot):
    bot.add_cog(Streams(bot))
