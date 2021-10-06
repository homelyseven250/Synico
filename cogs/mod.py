from datetime import timedelta
from typing import Optional

import discord
from discord.ext import commands, tasks
from utils import (
    Mutes,
    UserConverter,
    Warnings,
    is_admin,
    is_mod,
    start_menu,
)


class Moderation(commands.Cog):
    """
    A module to provide utilities to moderators
    and server owners to assist with maintenance.
    """

    def __init__(self, bot) -> None:
        self.bot = bot
        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self) -> None:
        """
        |coro|

        An asynchronous version of :method:`__init__`
        to access coroutines.
        """
        self.mute_role = {
            guild: role
            for guild, role in await self.bot.pool.fetch(
                "SELECT guild, mute FROM guilds"
            )
        }

        self.muted = {
            guild: {member: duration}
            for guild, member, duration in await self.bot.pool.fetch(
                "SELECT guild, user, ends FROM mutes"
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

            muted_guild = self.muted[guild].copy()
            for key, value in muted_guild.items():

                current_time = discord.utils.utcnow()
                if current_time > value or current_time == value:

                    guild: discord.Guild = self.bot.get_guild(guilds)
                    role: discord.Role = guild.get_role(self.mute_role[guild.id])
                    member: discord.Member = self.bot.cache["member"].get(
                        key, None
                    ) or await guild.fetch_member(key)

                    await self.bot.pool.execute(
                        "DELETE FROM mutes WHERE guild = $1 AND user = $2",
                        guild.id,
                        key,
                    )

                    del self.muted[guild][key]

                    if member and role:
                        try:
                            await member.remove_roles(role)
                        except (discord.Forbidden, discord.HTTPException):
                            pass

    @commands.command()
    @is_admin()
    async def ban(
        self, context: commands.Context, member: UserConverter, *, reason: str = None
    ) -> None:
        """
        Allows admins/owners to ban a user from a guild.
        """
        await context.guild.ban(member, reason=reason)
        await context.send(f"Banned {member}")

    @commands.command()
    @is_admin()
    async def unban(
        self, context: commands.Context, member: UserConverter, *, reason: str = None
    ) -> None:
        """
        Allows admins/owners to unban a user from a guild.
        """
        await context.guild.unban(member, reason=reason)
        await context.send(f"Unbanned {member}")

    @commands.command()
    @is_mod()
    async def kick(
        self, context: commands.Context, member: UserConverter, *, reason: str = None
    ) -> None:
        """
        Allows moderators/admins/owners to kick a user from a guild.
        """
        await context.guild.kick(member, reason=reason)
        await context.send(f"Kicked {member}")

    @commands.command()
    @is_mod()
    async def clear(
        self,
        context: commands.Context,
        channel: Optional[discord.TextChannel] = None,
        member: Optional[discord.Member] = None,
        amount: int = 1,
    ) -> None:
        """
        Allows moderators/admins/owners to remove up to 1000
        channel messages.
        """
        amount = amount if amount <= 1000 else 1000
        channel: discord.TextChannel = channel or context.channel

        def check(message: discord.Message):
            return message.author.id == member.id

        await channel.purge(limit=amount, check=check if member else None)
        await context.send(f"{amount} message(s) cleared.")

    @commands.command()
    @is_mod()
    async def lock(
        self, context: commands.Context, *, channel: discord.TextChannel = None
    ) -> None:
        """
        Allows moderators/admins/owners to prevent messages from being
        sent in a channel.
        """
        channel: discord.TextChannel = channel or context.channel
        await channel.set_permissions(context.guild.default_role, send_messages=False)
        await context.send("🔒 Channel is locked.")

    @commands.command()
    @is_mod()
    async def unlock(
        self, context: commands.Context, *, channel: discord.TextChannel = None
    ) -> None:
        """
        Allows moderators/admins/owners to allow messages to be sent
        in a channel.
        """
        channel: discord.TextChannel = channel or context.channel
        await channel.set_permissions(context.guild.default_role, send_messages=None)
        await context.send("🔓 Channel is unlocked.")

    @commands.command()
    @is_mod()
    async def slowmode(
        self,
        context: commands.Context,
        channel: Optional[discord.TextChannel] = None,
        *,
        duration: int = None,  # Placeholder typehint until I rework time converter.
    ) -> None:
        """
        Allows moderators/admins/owners to set a channel's slowmode delay.
        """
        channel: discord.TextChannel = channel or context.channel

        await channel.edit(slowmode_delay=duration)
        await context.send(
            f"Slowmode for {channel.mention} has been updated. Slowmode duration: "
            + duration
            or "disabled."
        )

    @commands.command()
    @is_mod()
    async def warn(
        self, context: commands.Context, member: UserConverter, *, reason: str = None
    ) -> None:
        """
        Allows moderators/admins/owners to give a warning to a user.
        """
        member: discord.Member = member
        warning = (
            await context.bot.pool.fetchval(
                "SELECT warned FROM warns WHERE guild = $1 AND user = $2 ORDER BY warned DESC;",
                context.guild.id,
                member.id,
            )
            or 0
        )

        await context.bot.pool.execute(
            "INSERT INTO warns (guild, user, author, warn, warned, created) VALUES ($1, $2, $3, $4, $5, $6)",
            context.guild.id,
            member.id,
            context.author.id,
            reason or "No reason provided.",
            warning + 1,
            discord.utils.utcnow(),
        )

        sent = True
        try:
            await member.send(
                f"**You have received a warning in {context.guild}{f', reason: {reason}' if reason else ''}**"
            )
        except discord.Forbidden:
            sent = False

        embed: discord.Embed = context.bot.embed(
            color=0xE74C3C,
            title=f"Warning #{warning + 1} issued to {member}",
            description=f"**{context.author} has issued a warning to {member} for the reason of:\n\n{reason or 'No reason provided.'}**",
        )
        embed.set_author(name=member.__str__(), url=member.avatar.url)
        if not sent:
            embed.set_footer(text=f"{member} did not receive message.")

        await context.send(embed=embed)

    @commands.command()
    @is_mod()
    async def warns(
        self, context: commands.Context, *, member: UserConverter = None
    ) -> None:
        """
        Allows moderators/admins/owners to view their own or others warnings.
        """
        member: discord.Member = member or context.author
        warns = await context.bot.pool.fetch(
            "SELECT * FROM warns WHERE guild = $1 AND user = $2 ORDER BY warned ASC;",
            context.guild.id,
            member.id,
        )
        if warns:
            await start_menu(context, Warnings(warns))

        else:
            await context.send(f"{member.mention} does not have any warnings.")

    @commands.command()
    @is_mod()
    async def unwarn(
        self, context: commands.Context, warn: int, *, member: UserConverter
    ) -> None:
        """
        Allows moderators/admins/owners to remove warnings from a user.
        """
        warning = await context.bot.pool.fetchval(
            "SELECT warned FROM warnings WHERE guild = $1 AND user = $2 AND warned = $3",
            context.guild.id,
            member.id,
            warn,
        )
        if warning:
            await context.bot.pool.execute(
                "DELETE FROM warns WHERE guild = $1 AND user = $2 AND warned = $3",
                context.guild.id,
                member.id,
                warn,
            )
            return await context.send(f"Deleted warning #{warn} from {member.mention}")

        await context.send(f"Warning #{warn} from {member.mention} does not exist.")

    @commands.command()
    @is_mod()
    async def mute(
        self,
        context: commands.Context,
        member: UserConverter,
        *,
        duration: int = None,  # Placeholder typehint until I rework time converter.
    ) -> None:
        """
        Allows moderators/admins/owners to mute a user.
        """
        member: discord.Member = member

        role: discord.Role = self.mute_role.get(context.guild.id)
        if not role:
            await context.send(
                f"Seems a muted role has not been setup. Please run `{context.prefix}muted @role` to setup."
            )
            return

        guild_mutes = self.muted.get(context.guild.id)
        if member.id in guild_mutes.keys():
            await context.send(f"{member.mention} is already muted.")
            return

        time = discord.utils.utcnow()
        timespan = None
        readable = None
        if duration:
            timespan = time + timedelta(seconds=duration)
            readable = discord.utils.format_dt(timespan, "R")

        if guild_mutes:
            self.muted[context.guild.id].update({member.id: timespan})

        else:
            self.muted[context.guild.id] = {member.id: timespan}

        await context.bot.pool.execute(
            "INSERT INTO mutes (guild, user, ends, starts, reason) VALUES ($1, $2, $3, $4, $5)",
            context.guild.id,
            member.id,
            timespan,
            time,
            readable,
        )

        await member.add_roles(role)
        try:
            await member.send(
                f"You were muted in {context.guild}\nDuration: " + readable
                or "indefinitely."
            )
        except discord.Forbidden:
            pass

        await context.send(
            f"{member.mention} was muted.\nDuration: " + readable or "indefinitely."
        )

    @commands.command()
    @is_mod()
    async def unmute(self, context: commands.Context, *, member: UserConverter) -> None:
        """
        Allows moderators/admins/owners to unmute a user.
        """
        member: discord.Member = member
        muted = self.muted.get(context.guild.id).copy()
        if member.id in muted.keys():

            role: discord.Role = context.guild.get_role(
                self.mute_role.get(context.guild.id)
            )

            if role in member.roles:

                try:
                    await member.remove_roles(role)
                except discord.Forbidden:
                    pass

            del self.muted[context.guild.id][member.id]
            await context.bot.pool.execute(
                "DELETE FROM mutes WHERE guild = $1 AND user = $2",
                context.guild.id,
                member.id,
            )

            try:
                await member.send(f"You were unmuted in {context.guild}")
            except discord.Forbidden:
                pass

            await context.send(f"{member.mention} has been unmuted.")

        else:
            await context.send(f"{member} is not muted.")

    @commands.command()
    @is_mod()
    async def mutes(self, context: commands.Context) -> None:
        """
        Allows moderators/admins/owners to view currently
        muted users and their mute duration.
        """
        mutes = await context.bot.pool.fetch(
            "SELECT * FROM mutes WHERE guild = $1", context.guild.id
        )
        if mutes:
            await start_menu(context, Mutes(mutes))

        else:
            await context.send(f"No users are muted in {context.guild}")


def setup(bot):
    bot.add_cog(Moderation(bot))
