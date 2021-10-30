import datetime
import pytz
import discord
from main import Bot
from discord.ext import commands, tasks


class Twitch(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        self.client_id = self.bot.config["TWITCH"]["client_id"]
        self.client_secret = self.bot.config["TWITCH"]["client_secret"]
        self.bot.loop.create_task(self.__ainit__())

    def cog_unload(self) -> None:
        self.check_streamers.stop()
        return super().cog_unload()

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        self.streamers = {
            streamer: {
                guild: {
                    "channel": await self.bot.pool.fetchval(
                        "SELECT twitch_channel FROM guilds WHERE guild = $1", guild
                    )
                    or 0,
                    "message": message,
                    "notified": bool(notified),
                }
            }
            for streamer, guild, message, notified in await self.bot.pool.fetch(
                "SELECT streamer, guild_id, live_message, notified FROM twitch"
            )
        }

        self.check_streamers.start()

    @tasks.loop(seconds=10, reconnect=True)
    async def check_streamers(self):
        if (
            not hasattr(self, "token_expired")
            or self.token_expired <= discord.utils.utcnow()
        ):
            oauth = f"https://id.twitch.tv/oauth2/token?client_id={self.client_id}&client_secret={self.client_secret}&grant_type=client_credentials&scope="
            async with self.bot.cs.post(oauth) as request:
                data: dict = await request.json()

            self.access_token: str = data.get("access_token")  # type:ignore
            token_expiration: int = data.get("expires_in")
            self.token_expired = discord.utils.utcnow() + datetime.timedelta(
                seconds=token_expiration
            )

            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Client-Id": self.client_id,
            }

        streamer_list = [streamer for streamer in self.streamers.keys()]
        _slice = 90
        for splice in range(0, len(streamer_list), _slice):
            streamers_parsed = ""
            for index, streamer in enumerate(streamer_list[splice : splice + _slice]):
                if index == 0:
                    streamers_parsed += "user_login=" + streamer

                else:
                    streamers_parsed += "&user_login=" + streamer

            async with self.bot.cs.get(
                "https://api.twitch.tv/helix/streams?" + streamers_parsed,
                headers=self.headers,
            ) as request:
                data: dict = await request.json()

            for streamer in data.get("data"):
                live = streamer.get("type")
                name = streamer.get("user_name")
                game = streamer.get("game_name")
                title = streamer.get("title")
                viewers = streamer.get("viewer_count")
                preview = streamer.get("thumbnail_url")
                started = streamer.get("started_at")

                started_parsed = datetime.datetime.fromisoformat(started[:-1])

                seconds = discord.utils.utcnow() - started_parsed.replace(
                    tzinfo=pytz.UTC
                )
                started_parsed = discord.utils.utcnow() - datetime.timedelta(
                    seconds=seconds.total_seconds()
                )

                for guild in iter(self.streamers[name.lower()]):
                    channel = self.streamers[name.lower()][guild]["channel"]
                    message = self.streamers[name.lower()][guild]["message"]
                    notified = self.streamers[name.lower()][guild]["notified"]

                    if name.lower() not in streamer_list or live.lower() != "live":
                        self.streamers[name.lower()][guild]["notified"] = False
                        await self.bot.pool.execute(
                            "UPDATE twitch SET notified = $1 WHERE guild_id = $2 AND streamer = $3",
                            False,
                            guild,
                            name.lower(),
                        )
                        continue

                    elif notified is True:
                        continue

                    else:
                        _channel = self.bot.get_channel(channel)
                        if _channel:

                            start_relative = discord.utils.format_dt(
                                started_parsed, "R"
                            )
                            start_date = discord.utils.format_dt(started_parsed)

                            async with self.bot.cs.get(
                                f"https://api.twitch.tv/helix/users?login={streamer.get('user_login')}",
                                headers=self.headers,
                            ) as request:
                                data = await request.json()

                            avatar = data["data"][0].get("profile_image_url")

                            embed: discord.Embed = self.bot.embed(
                                description=title,
                                color=0x2ECC71,
                                timestamp=started_parsed,
                            )
                            embed.set_thumbnail(url=avatar)
                            embed.set_image(url=preview.format(width=1920, height=1080))
                            embed.set_author(
                                name=name,
                                url=f"https://twitch.tv/{name}",
                                icon_url=avatar,
                            )

                            embed.add_field(name="Game", value=game)
                            embed.add_field(name="Viewers", value=viewers)
                            embed.add_field(
                                name="Uptime",
                                value=f"{start_date} ({start_relative})",
                            )

                            await _channel.send(
                                content=message,
                                embed=embed,
                                allowed_mentions=discord.AllowedMentions.all(),
                            )

                            self.streamers[name.lower()][guild]["notified"] = True
                            await self.bot.pool.execute(
                                "UPDATE twitch SET notified = $1 WHERE guild_id = $2 AND streamer = $3",
                                True,
                                guild,
                                name.lower(),
                            )
                            continue

    @commands.group()
    async def twitch(self, context: commands.Context):
        pass

    @twitch.group(name="update")
    async def twitch_update(self, context: commands.Context):
        pass

    @twitch_update.command(name="message")
    async def update_streamer(
        self,
        context: commands.Context,
        streamer: str = commands.Option(description="Name of Twitch streamer."),
        message: str = commands.Option(
            None, description="Notification message to send when a streamer is live."
        ),
    ):
        """
        Update the message sent when a streamer goes live.
        """
        is_following = await context.bot.pool.fetch(
            "SELECT streamer FROM twitch WHERE guild_id = $1 AND streamer = $2",
            context.guild.id,
            streamer.lower(),
        )
        if not is_following:
            await context.send(
                f"{context.guild} is not following {streamer}", ephemeral=True
            )
            return

        channel = await context.bot.pool.fetchval(
            "SELECT twitch_channel FROM guilds WHERE guild = $1", context.guild.id
        )

        self.streamers[streamer.lower()].update(
            {
                context.guild.id: {
                    "message": message or "",
                    "channel": channel,
                    "notified": self.streamers[streamer.lower()][context.guild.id][
                        "notified"
                    ],
                }
            }
        )
        await context.bot.pool.execute(
            "UPDATE twitch SET live_message = $1 WHERE guild = $1 AND streamer = $2",
            context.guild.id,
            streamer.lower(),
        )
        await context.send(
            f"Updated live message for {streamer}\n\n{message}", ephemeral=True
        )

    @twitch.command(name="follow")
    async def twitch_follow(
        self,
        context: commands.Context,
        streamer: str = commands.Option(
            description="Name of Twitch streamer to follow."
        ),
        message: str = commands.Option(
            None, description="Notification message to send when a streamer is live."
        ),
    ):
        """
        Follow a streamer and be notified when they go live.
        """
        is_following = await context.bot.pool.fetch(
            "SELECT streamer FROM twitch WHERE guild_id = $1 AND streamer = $2",
            context.guild.id,
            streamer.lower(),
        )
        if is_following:
            await context.send(
                f"{context.guild} is already following {streamer}", ephemeral=True
            )
            return

        await context.bot.pool.execute(
            "INSERT INTO twitch VALUES ($1, $2, $3, $4)",
            context.guild.id,
            streamer.lower(),
            message,
            False,
        )
        channel = await context.bot.pool.fetchval(
            "SELECT twitch_channel FROM guilds WHERE guild = $1", context.guild.id
        )

        if not self.streamers.get(streamer.lower()):
            self.streamers[streamer.lower()] = {}

        self.streamers[streamer.lower()].update(
            {
                context.guild.id: {
                    "channel": channel or 0,
                    "message": message or "",
                    "notified": False,
                }
            }
        )

        await context.send(
            f"{context.guild} is now following {streamer}", ephemeral=True
        )

    @twitch.command(name="unfollow")
    async def twitch_unfollow(
        self,
        context: commands.Context,
        streamer: str = commands.Option(
            description="Name of Twitch streamer to unfollow."
        ),
    ):
        """
        Unfollow a streamer and no longer be notified when they're live.
        """
        is_following = await context.bot.pool.fetch(
            "SELECT streamer FROM twitch WHERE guild_id = $1 AND streamer = $2",
            context.guild.id,
            streamer.lower(),
        )
        if is_following:
            self.streamers[streamer.lower()].pop(context.guild.id)
            await context.bot.pool.execute(
                "DELETE FROM twitch WHERE guild_id = $1 AND streamer = $2",
                context.guild.id,
                streamer.lower(),
            )
            await context.send(
                f"{context.guild} has unfollowed {streamer}", ephemeral=True
            )
            return

        await context.send(
            f"{context.guild} is not following {streamer}", ephemeral=True
        )


def setup(bot: Bot):
    bot.add_cog(Twitch(bot))
