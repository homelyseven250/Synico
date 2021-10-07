import discord
from discord.ext import commands
from utils import RoleConverter, guild_bot_owner, guild_owner, is_admin


class Settings(commands.Cog):
    """
    A module to allow configuring guild settings.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @guild_bot_owner()
    async def prefix(self, context: commands.Context, *, prefix: str) -> None:
        """
        Update the guild's prefix.
        """
        if prefix != context.bot.prefix.get(context.guild.id, context.bot.prefix):
            context.bot.prefix.update({context.guild.id: prefix})
            await context.bot.pool.execute(
                "UPDATE guilds SET prefix = $1 WHERE guild = $2",
                prefix,
                context.guild.id,
            )

            escaped_prefix = discord.utils.escape_markdown(prefix)
            await context.send(f"Prefix updated to {escaped_prefix}")

    @commands.command()
    @guild_owner()
    async def admin(self, context: commands.Context, *, role: RoleConverter) -> None:
        """
        Update the guild's admin role.
        """
        role: discord.Role = role
        await context.bot.pool.execute(
            "UPDATE guilds SET admin = $1 WHERE guild = $2", role.id, context.guild.id
        )
        await context.send(
            f"{role.mention} has been set as the admin role and will be able to use all moderation commands.",
        )

    @commands.command()
    @guild_owner()
    async def mod(self, context: commands.Context, *, role: RoleConverter) -> None:
        """
        Update the guild's mod role.
        """
        role: discord.Role = role
        await context.bot.pool.execute(
            "UPDATE guilds SET mod = $1 WHERE guild = $2", role.id, context.guild.id
        )
        await context.send(
            f"{role.mention} has been set as the mod role and will be able to use most moderation commands."
        )

    @commands.command()
    @is_admin()
    async def muted(self, context: commands.Context, *, role: RoleConverter) -> None:
        """
        Update the guild's muted role.
        """
        role: discord.Role = role
        await context.bot.pool.execute(
            "UPDATE guilds SET mute = $1 WHERE guild = $2",
            role.id,
            context.guild.id,
        )
        context.bot.mute_role.update({context.guild.id: role.id})
        await context.send(
            f"{role.mention} has been set as the muted role.",
        )

    @commands.command()
    @is_admin()
    async def logs(
        self, context: commands.Context, *, channel: discord.TextChannel = None
    ):
        """
        Update the guild's logging channel.
        """
        channel: discord.TextChannel = channel or context.channel
        await context.bot.pool.execute(
            "UPDATE guild SET logs = $1 WHERE guild_id = $2",
            channel.id,
            context.guild.id,
        )
        await context.send(f"Events will now be logged in {channel.mention}")


def setup(bot):
    bot.add_cog(Settings(bot))
