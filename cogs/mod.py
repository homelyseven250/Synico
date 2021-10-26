import datetime
from datetime import timedelta
from typing import Any, Optional

import discord
from discord.ext import commands, tasks
from main import Bot
from utils import (
    BannedUserConverter,
    MemberConverter,
    SlowmodeConverter,
    TimeConverter,
    UserConverter,
    generate_uuid,
)

from cogs.errors import is_admin, is_mod


class Moderation(commands.Cog):
    """
    A module to provide utilities to mods
    and server owners to assist with maintenance.
    """

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self) -> None:
        """
        |coro|

        An asynchronous version of :method:`__init__`
        to access coroutines.
        """
        await self.bot.wait_until_ready()

        self.bot.mute_role: dict[int, int] = {  # type: ignore
            guild: role
            for guild, role in await self.bot.pool.fetch(
                "SELECT guild, mute FROM guilds"
            )
        }

        self.muted: dict[int, dict[int, datetime.datetime]] = {
            guild: {member: duration}
            for guild, member, duration in await self.bot.pool.fetch(
                "SELECT guild, muted, ends FROM mutes"
            )
        }

        await self.check_mutes.start()

    def cog_unload(self) -> None:
        """
        This method is called before the extension is unloaded
        to allow for the running task loop to gracefully
        close after finishing final iteration.
        """
        self.check_mutes.stop()
        return super().cog_unload()

    @tasks.loop(seconds=10, reconnect=True)
    async def check_mutes(self) -> None:
        """
        |coro|

        A running task loop that repeats after each iteration
        asynchronously to to check if a user's mute duration
        has been met and can be unmuted.
        """
        muted = self.muted.copy()
        for guilds in iter(muted):

            muted_guild = self.muted[guilds].copy()
            for key, value in muted_guild.items():
                if value is None:
                    continue

                current_time = discord.utils.utcnow()
                if current_time >= value:
                    try:

                        guild: discord.Guild = self.bot.get_guild(guilds)
                        role: discord.Role = guild.get_role(
                            self.bot.mute_role.get(guild.id)
                        )
                        member: discord.Member = self.bot.cache["member"].get(
                            key, None
                        ) or await guild.fetch_member(key)

                        await self.bot.pool.execute(
                            "DELETE FROM mutes WHERE guild = $1 AND muted = $2",
                            guild.id,
                            key,
                        )

                        if member and role:
                            try:
                                await member.remove_roles(role)
                            except (discord.Forbidden, discord.HTTPException):
                                pass

                        del self.muted[guilds][key]
                    except (discord.Forbidden, discord.HTTPException, discord.NotFound):
                        del self.muted[guilds][key]

    @check_mutes.before_loop
    async def before_check_mutes(self) -> None:
        await self.bot.wait_until_ready()

    @commands.group()
    async def ban(self, context: commands.Context) -> None:
        pass

    @ban.command(name="id")
    @is_admin()
    async def ban_id(
        self,
        context: commands.Context,
        user_id: str = commands.Option(name="id", description="ID of user to ban."),
        delete_message_days: int = commands.Option(
            None,
            description="The number of days of messages to delete from the user. Input can only be between 0-10.",
        ),
        reason: str = commands.Option(None, description="Reason for ban."),
    ) -> None:
        """
        Allows admins/owners to ban a user from a server by ID.
        """
        delete_message_days = (
            0
            if not delete_message_days
            or delete_message_days < 0
            or delete_message_days > 10
            else delete_message_days
        )
        try:
            _id = int(user_id)
            await context.guild.ban(
                discord.Object(_id),
                delete_message_days=delete_message_days,
                reason=reason,
            )
            embed: discord.Embed = context.bot.embed(
                description=f"<@{_id}> has been banned. Reason: {reason or 'no reason provided.'}",
                color=0xE74C3C,
                timestamp=discord.utils.utcnow(),
            )
            await context.send(embed=embed)
        except (ValueError, discord.Forbidden, discord.HTTPException) as error:
            await context.send(error.text)

    @ban.command(name="user")
    @is_admin()
    async def ban_user(
        self,
        context: commands.Context,
        username: str = commands.Option(
            description="Username and discriminator of user to ban."
        ),
        delete_message_days: int = commands.Option(
            None,
            description="The number of days of messages to delete from the user. Input can only be between 0-10.",
        ),
        reason: str = commands.Option(None, description="Reason for ban"),
    ) -> None:
        """
        Allows admins/owners to ban a user from a server by their username#discriminator.
        """
        user = await MemberConverter().convert(
            context, username
        ) or await UserConverter().convert(context, username)
        if user:
            delete_message_days = (
                0
                if not delete_message_days
                or delete_message_days < 0
                or delete_message_days > 10
                else delete_message_days
            )
            await context.guild.ban(
                user,
                delete_message_days=delete_message_days,
                reason=reason,
            )
            embed: discord.Embed = context.bot.embed(
                description=f"{user} has been banned. Reason: {reason or 'no reason provided.'}",
                color=0xE74C3C,
                timestamp=discord.utils.utcnow(),
            )
            await context.send(embed=embed)
            return

        raise commands.UserNotFound(username)

    @ban.command(name="member")
    @is_admin()
    async def ban_member(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(description="Server member to ban."),
        delete_message_days: int = commands.Option(
            None,
            description="The number of days of messages to delete from the user. Input can only be between 0-10.",
        ),
        reason: str = commands.Option(None, description="Reason for ban."),
    ) -> None:
        """
        Allows admins/owners to ban a member from a server.
        """
        delete_message_days = (
            0
            if not delete_message_days
            or delete_message_days < 0
            or delete_message_days > 10
            else delete_message_days
        )
        await context.guild.ban(
            member,
            delete_message_days=delete_message_days,
            reason=reason,
        )
        embed: discord.Embed = context.bot.embed(
            description=f"{member} has been banned. Reason: {reason or 'no reason provided.'}",
            color=0xE74C3C,
            timestamp=discord.utils.utcnow(),
        )
        await context.send(embed=embed)

    @commands.group()
    async def unban(self, context: commands.Context) -> None:
        pass

    @unban.command(name="id")
    @is_admin()
    async def unban_id(
        self,
        context: commands.Context,
        id: str = commands.Option(description="ID of user to unban."),
        reason: str = commands.Option(None, description="Reason for unban."),
    ) -> None:
        """
        Allows admins/owners to unban a user from a server by ID.
        """
        try:
            _id = int(id)
            await context.guild.unban(discord.Object(_id), reason=reason)
            embed: discord.Embed = context.bot.embed(
                description=f"<@{_id}> has been unbanned. Reason: {reason or 'no reason provided.'}",
                color=0xE67E22,
                timestamp=discord.utils.utcnow(),
            )
            await context.send(embed=embed)
        except (ValueError, discord.Forbidden, discord.HTTPException) as error:
            await context.send(error.text)

    @unban.command(name="user")
    @is_admin()
    async def unban_user(
        self,
        context: commands.Context,
        username: str = commands.Option(
            description="Username and discriminator of user to unban."
        ),
        reason: str = commands.Option(None, description="Reason for unban."),
    ) -> None:
        """
        Allows admins/owners to unban a user from a server by username#discriminator.
        """
        user = (
            await MemberConverter().convert(context, username)
            or await UserConverter().convert(context, username)
            or await BannedUserConverter().convert(context, username)
        )
        if user:
            await context.guild.unban(user, reason=reason)
            embed: discord.Embed = context.bot.embed(
                description=f"{username} has been unbanned. Reason: {reason or 'no reason provided.'}",
                color=0xE67E22,
                timestamp=discord.utils.utcnow(),
            )
            await context.send(embed=embed)
            return

        raise commands.UserNotFound(username)

    @commands.command()
    @is_mod()
    async def kick(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(description="Server member to kick."),
        reason: str = commands.Option(None, description="Reason for kick."),
    ) -> None:
        """
        Allows mods/admins/owners to kick a user from a guild.
        """
        await context.guild.kick(member, reason=reason)
        embed: discord.Embed = context.bot.embed(
            description=f"{member} has been kicked. Reason: {reason or 'no reason provided.'}",
            color=0xE67E22,
            timestamp=discord.utils.utcnow(),
        )
        await context.send(embed=embed)

    @commands.command()
    async def clear(
        self,
        context: commands.Context,
        channel: discord.TextChannel = commands.Option(
            None, description="Text channel to clear messages in."
        ),
        amount: int = commands.Option(
            description="Amount of messages to clear. Amount can only be between 1-1000."
        ),
    ) -> None:
        """
        Allows mods/admins/owners to remove up to 1000
        channel messages.
        """
        _channel = channel or context.channel
        _amount = amount + 1 if amount == 0 else 1000 if amount > 1000 else amount

        deleted: int = 0
        messages = await _channel.purge(limit=_amount)
        deleted += len(messages)

        await context.send(f"Cleared {deleted} messages.", ephemeral=True)

    @commands.command()
    @is_mod()
    async def lock(
        self,
        context: commands.Context,
        channel: discord.TextChannel = commands.Option(
            None, description="Channel to lock."
        ),
        all_channels: bool = commands.Option(
            None, description="Whether to lock all channels or not."
        ),
    ) -> None:
        """
        Allows mods/admins/owners to prevent messages from being
        sent in a channel.
        """
        if all_channels:
            for channel in context.guild.text_channels:
                try:
                    await channel.set_permissions(
                        context.guild.default_role, send_messages=False
                    )
                except (
                    discord.Forbidden,
                    discord.HTTPException,
                    discord.NotFound,
                    discord.InvalidArgument,
                ):
                    continue

            await context.send("🔒 All channels are now locked.", ephemeral=True)

        else:
            channel: discord.TextChannel = channel or context.channel
            await channel.set_permissions(
                context.guild.default_role, send_messages=False
            )
            await context.send("🔒 Channel is now locked.", ephemeral=True)

    @commands.command()
    @is_mod()
    async def unlock(
        self,
        context: commands.Context,
        channel: discord.TextChannel = commands.Option(
            None, description="Channel to unlock."
        ),
        all_channels: bool = commands.Option(
            None, description="Whether to unlock all channels or not."
        ),
    ) -> None:
        """
        Allows mods/admins/owners to allow messages to be sent
        in a channel.
        """

        if all_channels:
            for channel in context.guild.text_channels:
                try:
                    await channel.set_permissions(
                        context.guild.default_role, send_messages=None
                    )
                except (
                    discord.Forbidden,
                    discord.HTTPException,
                    discord.NotFound,
                    discord.InvalidArgument,
                ):
                    continue

            await context.send("🔒 All channels are now unlocked.", ephemeral=True)

        else:
            channel: discord.TextChannel = channel or context.channel
            await channel.set_permissions(
                context.guild.default_role, send_messages=None
            )
            await context.send("🔒 Channel is now unlocked.", ephemeral=True)

    @commands.command()
    @is_mod()
    async def slowmode(
        self,
        context: commands.Context,
        channel: discord.TextChannel = commands.Option(
            None, description="Channel to enable/disable slowmode in."
        ),
        duration: SlowmodeConverter = commands.Option(
            None,
            description="Amount of time for slowmode. No input will remove slowmode.",
        ),
    ) -> None:
        """
        Allows mods/admins/owners to set a channel's slowmode delay.
        """
        channel: discord.TextChannel = channel or context.channel

        await channel.edit(slowmode_delay=duration)
        await context.send(
            f"Slowmode for {channel.mention} has been updated. Slowmode{f'duration: {duration} seconds' if duration else ' disabled.'}",
            ephemeral=True,
        )

    @commands.group()
    @is_mod()
    async def warn(self, context: commands.Context) -> None:
        pass

    @warn.command(name="member")
    async def warn_member(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(
            description="Server member to give a warning to."
        ),
        reason: str = commands.Option(None, description="Reason for warning."),
    ) -> None:
        """
        Allows mods/admins/owners to give a warning to a user.
        """
        warning_id = await generate_uuid(context)
        warning: int = (
            await context.bot.pool.fetchval(
                "SELECT warning_num FROM warns WHERE guild = $1 AND warned = $2 ORDER BY warned DESC;",
                context.guild.id,
                member.id,
            )
            or 0
        )

        await context.bot.pool.execute(
            "INSERT INTO warns VALUES ($1, $2, $3, $4, $5, $6, $7)",
            context.guild.id,
            member.id,
            context.author.id,
            reason or "No reason provided.",
            warning + 1,
            discord.utils.utcnow(),
            warning_id,
        )

        sent = True
        try:
            await member.send(
                f"You were warned in {context.guild}{f', reason: {reason}' if reason else ''}"
            )
        except (discord.Forbidden, discord.HTTPException):
            sent = False

        embed: discord.Embed = context.bot.embed(
            color=0xE74C3C,
            description=f"{context.author} warned {member} [warning {warning + 1}]\n\n{reason or ''}",
        )
        if not sent:
            embed.set_footer(
                text=f"{member} did not receive the message. {member} has either blocked me or closed dms."
            )

        await context.send(embed=embed)

    @warn.command(name="remove")
    @is_mod()
    async def warn_remove(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(
            description="Server member to remove warning from."
        ),
        id: int = commands.Option(description="ID of warning."),
    ) -> None:
        """
        Allows mods/admins/owners to remove warnings from a user.
        """
        warning: int = await context.bot.pool.fetchval(
            "SELECT warning FROM warns WHERE guild = $1 AND warned = $2 AND warning_id = $3",
            context.guild.id,
            member.id,
            id,
        )
        if warning:
            await context.bot.pool.execute(
                "DELETE FROM warns WHERE guild = $1 AND warned = $2 AND warning_id = $3",
                context.guild.id,
                member.id,
                id,
            )
            return await context.send(
                f"Deleted warning #{warning} from {member.mention}", ephemeral=True
            )

        await context.send(
            f"{id} does not belong to any warning from {member.mention}", ephemeral=True
        )

    @commands.group()
    async def mute(self, context: commands.Context) -> None:
        pass

    @mute.command(name="member")
    async def mute_member(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(description="Server member to mute."),
        duration: TimeConverter = commands.Option(
            None,
            description="Amount of time to mute member. No input will be indefinite.",
        ),
        reason: str = commands.Option(None, description="Reason for muting member."),
    ) -> None:
        """
        Allows mods/admins/owners to mute a user.
        """
        muted_role_id: Optional[int] = self.bot.mute_role.get(context.guild.id)
        role: discord.Role = context.guild.get_role(muted_role_id)
        if not role:
            await context.send(
                f"Seems a muted role has not been setup. Please run `/settings muted @role` to setup.",
                ephemeral=True,
            )
            return

        guild_mutes = self.muted.get(context.guild.id)
        if guild_mutes and member.id in guild_mutes.keys():
            await context.send(f"{member.mention} is already muted.", ephemeral=True)
            return

        current_time = discord.utils.utcnow()
        mute_duration = None
        readable_date = None
        readable_time = None
        if duration is not None:
            mute_duration = current_time + timedelta(seconds=duration)
            readable_date = discord.utils.format_dt(mute_duration)
            readable_time = discord.utils.format_dt(mute_duration, "R")

        if guild_mutes:
            self.muted[context.guild.id].update({member.id: mute_duration})

        else:
            self.muted[context.guild.id] = {member.id: mute_duration}

        await context.bot.pool.execute(
            "INSERT INTO mutes VALUES ($1, $2, $3, $4, $5)",
            context.guild.id,
            member.id,
            mute_duration,
            current_time,
            reason,
        )

        await member.add_roles(role)
        try:
            await member.send(
                f"You were muted in {context.guild}{f' for {reason}' if reason else ''}. {f'Mute ends {readable_time} on {readable_date}' if readable_time else ''}"
            )
        except discord.Forbidden:
            pass

        await context.send(
            f"{member.mention} was muted. {f'Mute ends {readable_time} on {readable_date}' if readable_time else ''}"
        )

    @mute.command(name="remove")
    @is_mod()
    async def mute_remove(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(
            description="Server member to unmute."
        ),
    ) -> None:
        """
        Allows mods/admins/owners to unmute a user.
        """
        muted = self.muted.get(context.guild.id).copy()
        if member.id in muted.keys():

            role: discord.Role = context.guild.get_role(
                self.bot.mute_role.get(context.guild.id)
            )

            if role in member.roles:
                try:
                    await member.remove_roles(role)
                except discord.Forbidden:
                    pass

            del self.muted[context.guild.id][member.id]
            await context.bot.pool.execute(
                "DELETE FROM mutes WHERE guild = $1 AND muted = $2",
                context.guild.id,
                member.id,
            )

            try:
                await member.send(f"You were unmuted in {context.guild}")
            except discord.Forbidden:
                pass

            await context.send(
                f"{member.mention} has been unmuted.",
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=True, roles=False, replied_user=True
                ),
            )
            return

        await context.send(f"{member} is not muted.", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(Moderation(bot))
