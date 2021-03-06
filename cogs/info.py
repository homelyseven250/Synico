from typing import List, Optional, Union

import discord
from discord.ext import commands
from main import Bot
from utils import Mutes, Tags, UserConverter, Warnings, start_menu

from cogs.errors import is_mod, tag_perms


class Info(commands.Cog):
    """
    A module to provide information
    on users and servers with handy utilities.
    """

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        self.lastfm_key = api_key = self.bot.config["LASTFM"]["api_key"]
        self.lastfm_users = {
            user: username
            for user, username in await self.bot.pool.fetch(
                "SELECT user_id, lastfm_user FROM lastfm"
            )
        }

    @commands.group(name="profile")
    async def user_info(self, context: commands.Context) -> None:
        pass

    @user_info.command(name="avatar")
    async def _avatar(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(
            None, description="Server member who's avatar to show."
        ),
    ) -> None:
        """
        Display a member's avatar.
        """
        member: discord.Member = member or context.author
        embed: discord.Embed = context.bot.embed(color=0x2ECC71)
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"{member}'s Avatar")
        await context.send(embed=embed)

    @user_info.command(name="banner")
    async def banner(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(
            None, description="Server member who's banner to show."
        ),
    ) -> None:
        """
        Display a member's banner
        """
        member = member or context.author

        async def get_cached_user(_id: int) -> discord.User:
            user: Optional[discord.User] = context.bot.cache["user"].get(_id)
            if isinstance(user, discord.User):
                return user

            fetched_user: discord.User = await context.bot.fetch_user(_id)
            context.bot.cache["user"].update({fetched_user.id: fetched_user})
            return await get_cached_user(fetched_user.id)

        user = await get_cached_user(member.id)
        banner = user.banner
        if banner is None:
            return await context.send(
                f"{member} does not have a banner.", ephemeral=True
            )

        embed: discord.Embed = context.bot.embed(color=0x2ECC71)
        embed.set_image(url=banner.url)
        embed.set_footer(text=f"{member}'s Banner")
        await context.send(embed=embed)

    @user_info.command(name="info")
    async def whois(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(
            None, description="Server member who's info to show."
        ),
    ) -> None:
        """
        Display information on a user.
        """
        member = member or context.author

        created = discord.utils.format_dt(member.created_at)
        created_since = discord.utils.format_dt(member.created_at, "R")

        joined = discord.utils.format_dt(member.joined_at)
        joined_since = discord.utils.format_dt(member.joined_at, "R")

        special_permissions = [
            "administrator",
            "ban_members",
            "kick_members",
            "manage_messages",
        ]
        permissions = ", ".join(
            [
                key.replace("_", " ").replace("guild", "server").title()
                for key, value in dict(
                    discord.Permissions(member.guild_permissions.value)
                ).items()
                if value and key in special_permissions
            ]
        )

        roles = ", ".join([role.mention for role in member.roles[1:43]])

        embed: discord.Embed = context.bot.embed(
            color=0x2ECC71,
            description=f"**Account Details**:\nJoined {context.guild} on {joined}\n({joined_since})\n\n \
            Registered Account on {created}\n({created_since})\n\n \
            **Key Permission(s)**:\n{permissions or 'N/A'}\n\n",
        )

        embed.add_field(name="Role(s)", value=roles[:1008] or "@everyone")
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)

        await context.send(embed=embed)

    @commands.group(name="lastfm")
    async def _lastfm(self, context: commands.Context):
        pass

    @_lastfm.command(name="link")
    async def lastfm_link(
        self,
        context: commands.Context,
        username: str = commands.Option(description="Username of last.fm account."),
    ):
        """
        Link your last.fm account.
        """

        user_info_url = "http://ws.audioscrobbler.com/2.0/?method=user.getinfo&user={user}&api_key={key}&format=json".format(
            user=username, key=self.lastfm_key
        )
        async with context.bot.cs.get(user_info_url) as r:
            data = await r.json()

        if not data.get("user"):
            await context.send(
                f"Could not locate your last.fm account.", ephemeral=True
            )
            return

        _username = data["user"]["name"]

        exists = self.lastfm_users.get(context.author.id)
        if not exists:
            await context.bot.pool.execute(
                "INSERT INTO lastfm VALUES ($1, $2)",
                context.author.id,
                username,
            )

        else:
            await context.bot.pool.execute(
                "UPDATE lastfm SET lastfm_user = $1 WHERE user_id = $2",
                username,
                context.author.id,
            )

        self.lastfm_users.update({context.author.id: _username})
        await context.send(
            f"Successfully linked {context.author} to https://last.fm/user/{_username}",
            ephemeral=True,
        )

    @commands.command(name="fm")
    async def _fm(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(
            None, description="Member to view recent last.fm activity."
        ),
    ):
        """
        View recent last.fm listening activity.
        """
        member = member or context.author
        if not self.lastfm_users.get(member.id):
            await context.send(
                f"{member} is not linked to a last.fm account. Use /lastfm link",
                ephemeral=True,
            )
            return

        user = self.lastfm_users.get(member.id)

        user_info_url = "http://ws.audioscrobbler.com/2.0/?method=user.getinfo&user={user}&api_key={key}&format=json".format(
            user=user, key=self.lastfm_key
        )
        recent_track_url = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={user}&api_key={key}&limit=1&format=json"
        user_track_url = "http://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key={key}&artist={artist}&track={track}&username={username}&format=json"

        async with context.bot.cs.get(user_info_url) as r:
            data = await r.json()

        if not data.get("user"):
            await context.send(
                f"Could not locate your last.fm account.", ephemeral=True
            )
            return

        username: str = data["user"]["name"]
        avatar_url: str = data["user"]["image"][-1]["#text"]
        profile_url: str = data["user"]["url"]

        async with context.bot.cs.get(
            recent_track_url.format(user=username, key=self.lastfm_key)
        ) as r:
            data = await r.json()

        if not len(data["recenttracks"]["track"]) >= 1:
            await context.send(
                "You do not have any recent listening activity.", ephemeral=True
            )
            return

        recent: dict = data["recenttracks"]["track"][0]
        track_name: str = recent["name"]
        track_url: str = recent["url"]
        track_cover: str = recent["image"][-1]["#text"]
        artist_name: str = recent["artist"]["#text"]

        album_name: str = recent["album"]["#text"]

        async with context.bot.cs.get(
            user_track_url.format(
                key=self.lastfm_key,
                artist=artist_name,
                track=track_name.replace(" ", "+"),
                username=username,
            ).replace(" ", "+")
        ) as r:
            data = await r.json()

        embed: discord.Embed = context.bot.embed(color=0x2ECC71)

        total_plays: int = data["track"]["playcount"] if data.get("track") else 0
        user_plays: int = data["track"]["userplaycount"] if data.get("track") else 0

        album_url: Optional[str] = (
            None if not data.get("track") else data["track"]["album"]["url"]
        )
        album_image: Optional[str] = (
            data["track"]["album"]["image"][-1]["#text"] if data.get("track") else None
        )

        album_hyperlink = (
            album_name if not album_url else f"[{album_name}]({album_url})"
        )

        embed.add_field(
            name="Track/Album",
            value=f"[{track_name}]({track_url}) - {album_hyperlink}",
            inline=False,
        )
        embed.add_field(
            name="Artist",
            value=f"[{artist_name}](https://www.last.fm/music/{artist_name.replace(' ', '+')})",
        )

        embed.set_author(name=username, url=profile_url, icon_url=avatar_url)
        embed.set_thumbnail(url=track_cover)
        embed.set_footer(
            text=f"{username}'s Plays: {user_plays} | Total Plays: {total_plays}",
            icon_url=album_image or track_cover,
        )

        await context.send(embed=embed)

    @commands.command(name="serverinfo")
    async def server_info(self, context: commands.Context) -> None:
        """
        Display information on the server.
        """
        guild: discord.Guild = context.guild

        created = discord.utils.format_dt(guild.created_at)
        created_since = discord.utils.format_dt(guild.created_at, "R")

        animated = len([emoji for emoji in guild.emojis if emoji.animated])
        static = len([emoji for emoji in guild.emojis if not emoji.animated])
        emojis = f"{len(guild.emojis)}/{guild.emoji_limit}"
        features = ", ".join(guild.features).lower().title()

        upload_limit = f"{round(guild.filesize_limit / 1000000)} MB"
        members = guild.member_count

        mfa = {0: "Admins don't require 2FA.", 1: "Admins required 2FA."}
        mfa = mfa[guild.mfa_level]

        verify = {
            0: "No requirements.",
            1: "Verified email required.",
            2: "Verified email and account age greater than 5 minutes required.",
            3: "Verified email, account age greater than 5 minutes, and a member of the server for 10 minutes required.",
            4: "Verified email, account age greater than 5 minutes, a member of the server for 10 minutes, and a verified phone number required.",
        }
        verification = verify[guild.verification_level.value]

        region = guild.region.value.replace("-", " ").title()
        roles = len(guild.roles)

        text = len(guild.text_channels)
        voice = len(guild.voice_channels)
        channels = len(guild.channels)
        categories = len(guild.categories)

        embed: discord.Embed = context.bot.embed(
            color=0x2ECC71,
            description=f"Server created on {created} ({created_since}) located in **{region}**\n\n \
            **Total Members:** {members}\n\n \
            **Text Channels:** {text}\n**Voice Channels:** {voice}\n**Total Channels:** {channels}\n**Total Categories:** {categories}\n\n \
            **Animated Emojis:** {animated}\n**Static Emojis:** {static}\n**Total Emojis:** {emojis}\n\n \
            **Total Roles:** {roles}\n**Upload Limit:** {upload_limit}\n**Admin MFA:** {mfa}\n**Server Verification:** {verification}\n\n \
            **Server Features:** {features or 'N/A'}",
        )

        embed.set_author(name=str(guild), icon_url=guild.icon.url)
        embed.set_thumbnail(url=guild.icon.url)

        await context.send(embed=embed)

    @commands.group()
    async def tag(self, context: commands.Context) -> None:
        pass

    @tag.command(name="name")
    async def tag_name(
        self,
        context: commands.Context,
        tag: str = commands.Option(description="Name of tag to search for."),
    ) -> None:
        """
        Display a tag.
        """
        tag = tag.lower()
        _tag: Optional[str] = await context.bot.pool.fetchval(
            "SELECT tag_content FROM tags WHERE guild = $1 AND tag_lower = $2",
            context.guild.id,
            tag,
        )

        if _tag:
            count: int = (
                await context.bot.pool.fetchval(
                    "SELECT used FROM tags WHERE guild = $1 AND tag_lower = $2",
                    context.guild.id,
                    tag,
                )
                or 0
            )
            await context.bot.pool.execute(
                "UPDATE tags SET used = $1 WHERE guild = $2 AND tag_lower = $3",
                count + 1,
                context.guild.id,
                tag,
            )

            return await context.send(
                content=_tag,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=False, roles=False, replied_user=True
                ),
            )

        await context.send("Could not find a tag with that name.", ephemeral=True)

    @tag.command(name="create")
    async def tag_create(
        self,
        context: commands.Context,
        tag: str = commands.Option(
            description="Name of tag. Can only be up to 1250 characters."
        ),
        content: str = commands.Option(
            description="Contents of tag. Can only be up to 2500 characters"
        ),
    ) -> None:
        """
        Create a tag.
        """
        if len(tag) > 1250:
            await context.send(
                f"Tag name exceeded character limit. ({len(tag)}/1250)", ephemeral=True
            )

        elif len(content) > 2500:
            await context.send(
                f"Tag content exceeded character limit. ({len(tag)}/2500)",
                ephemeral=True,
            )

        else:
            _tag: Optional[str] = await context.bot.pool.fetchval(
                "SELECT tag FROM tags WHERE guild = $1 AND tag_lower = $2",
                context.guild.id,
                tag.lower(),
            )
            if not _tag:
                await context.bot.pool.execute(
                    "INSERT INTO tags VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    context.guild.id,
                    context.author.id,
                    discord.utils.utcnow(),
                    0,
                    content[:2500],
                    tag[:1250],
                    tag.lower()[:1250],
                )
                return await context.send("Tag successfully created.", ephemeral=True)

            await context.send("Tag already exists.", ephemeral=True)

    @tag.command(name="info")
    async def tag_info(
        self,
        context: commands.Context,
        tag: str = commands.Option(description="Name of tag to find info on."),
    ) -> None:
        """
        Display info on a tag.
        """
        _tag: Optional[List] = await self.bot.pool.fetch(
            "SELECT * FROM tags WHERE guild = $1 AND tag_lower = $2",
            context.guild.id,
            tag.lower(),
        )
        if _tag:
            _tag = _tag[0]
            user = _tag["creator"]
            name = _tag["tag"]
            uses = _tag["used"]
            date = _tag["created"]
            contents = _tag["tag_content"]

            tag_owner: Union[discord.Member, str] = (
                self.bot.cache["member"].get(user)
                or await UserConverter.convert(user)
                or user
            )

            embed: discord.Embed = context.bot.embed(
                title=name[:256],
                description=f"{contents[:4000]}\n\n{discord.utils.format_dt(date)}",
                color=0x2ECC71,
            )
            embed.set_author(name=str(tag_owner), icon_url=tag_owner.display_avatar.url)
            embed.set_footer(text=f"Uses: {uses}")
            return await context.send(embed=embed, ephemeral=True)

        await context.send("Could not find a tag with that name.", ephemeral=True)

    @tag.command(name="delete")
    async def tag_delete(
        self,
        context: commands.Context,
        tag: str = commands.Option(description="Name of tag to delete."),
    ) -> None:
        """
        Delete a server's tag.
        """
        tag = tag.lower()
        _tag: Optional[List] = await self.bot.pool.fetch(
            "SELECT * FROM tags WHERE guild = $1 AND tag_lower = $2",
            context.guild.id,
            tag,
        )
        if _tag:
            _tag = _tag[0]
            permission_check = tag_perms(context, _tag["creator"])
            if permission_check:
                await self.bot.pool.execute(
                    "DELETE FROM tags WHERE guild = $1 AND tag_lower = $2",
                    context.guild.id,
                    tag,
                )
                await context.send("Tag has been deleted.", ephemeral=True)
                return

            await context.send(
                "You are not allowed to delete this tag.", ephemeral=True
            )
            return

        await context.send("Could not find a tag with that name.", ephemeral=True)

    @tag.command(name="edit")
    async def edit_tag(
        self,
        context: commands.Context,
        tag: str = commands.Option(description="Name of tag to edit."),
        content: str = commands.Option(description="Contents of tag to replace with."),
    ) -> None:
        """
        Edit the contents of a tag.
        """
        tag = tag.lower()
        if len(content) > 2500:
            await context.send(
                f"Tag content exceeded character limit. ({len(tag)}/2500)",
                ephemeral=True,
            )
            return

        _tag = await self.bot.pool.fetch(
            "SELECT * FROM tags WHERE guild = $1 AND tag_lower = $2",
            context.guild.id,
            tag,
        )
        if _tag:
            _tag = _tag[0]

            permission_check = tag_perms(context, _tag["creator"])
            if permission_check:
                await context.bot.pool.execute(
                    "UPDATE tags SET tag_content = $1 WHERE guild = $2 AND tag_lower = $3",
                    content,
                    context.guild.id,
                    tag,
                )
                await context.send(content="Tag has been updated.", ephemeral=True)
                return

            await context.send("You are not allowed to edit this tag.", ephemeral=True)
            return

        await context.send("Could not find a tag with that name.", ephemeral=True)

    @commands.group(name="show")
    async def _show(self, context: commands.Context) -> None:
        pass

    @_show.command(name="tags")
    async def show_tags(self, context: commands.Context) -> None:
        """
        Show server-made tags.
        """
        tags: Optional[List] = await context.bot.pool.fetch(
            "SELECT * FROM tags WHERE guild = $1", context.guild.id
        )
        if tags:
            await start_menu(context, Tags(tags))
            return

        await context.send(f"No tags created in {context.guild}", ephemeral=True)

    @_show.command(name="warnings")
    @is_mod()
    async def show_warnings(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(
            None, description="Server member who's warnings to show."
        ),
    ) -> None:
        """
        Allows mods/admins/owners to view their own or others warnings.
        """
        member = member or context.author
        warns: Optional[List] = await context.bot.pool.fetch(
            "SELECT * FROM warns WHERE guild = $1 AND warned = $2 ORDER BY warned ASC;",
            context.guild.id,
            member.id,
        )
        if warns:
            return await start_menu(context, Warnings(warns))

        await context.send(
            f"{member.mention} does not have any warnings.", ephemeral=True
        )

    @_show.command(name="mutes")
    @is_mod()
    async def mutes(self, context: commands.Context) -> None:
        """
        Allows mods/admins/owners to view currently
        muted users and their mute duration.
        """
        mutes: Optional[List] = await context.bot.pool.fetch(
            "SELECT * FROM mutes WHERE guild = $1", context.guild.id
        )
        if mutes:
            await start_menu(context, Mutes(mutes))
            return

        await context.send(f"No users are muted in {context.guild}", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(Info(bot))
