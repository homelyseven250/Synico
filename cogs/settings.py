import discord
from discord.ext import commands
from main import Bot

from cogs.errors import guild_owner, is_admin


class Settings(commands.Cog):
    """
    A module to allow configuring guild settings.
    """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(name="set")
    async def _settings(self, context: commands.Context) -> None:
        pass

    @_settings.command()
    @guild_owner()
    async def admin(
        self,
        context: commands.Context,
        role: discord.Role = commands.Option(
            description="Role to give access to all moderation commands."
        ),
    ) -> None:
        """
        Update the guild's admin role.
        """
        await context.bot.pool.execute(
            "UPDATE guilds SET admins = $1 WHERE guild = $2", role.id, context.guild.id
        )
        await context.send(
            f"{role.mention} has been set as the admin role and will be able to use all moderation commands.",
            ephemeral=True,
        )

    @_settings.command()
    @guild_owner()
    async def mod(
        self,
        context: commands.Context,
        role: discord.Role = commands.Option(
            description="Role to give access to most moderation commands."
        ),
    ) -> None:
        """
        Update the guild's mod role.
        """
        await context.bot.pool.execute(
            "UPDATE guilds SET mod = $1 WHERE guild = $2", role.id, context.guild.id
        )
        await context.send(
            f"{role.mention} has been set as the mod role and will be able to use most moderation commands.",
            ephemeral=True,
        )

    @_settings.command()
    @is_admin()
    async def muted(
        self,
        context: commands.Context,
        role: discord.Role = commands.Option(
            description="Designated role given to members when muted."
        ),
    ) -> None:
        """
        Update the guild's muted role.
        """
        await context.bot.pool.execute(
            "UPDATE guilds SET mute = $1 WHERE guild = $2",
            role.id,
            context.guild.id,
        )
        context.bot.mute_role.update({context.guild.id: role.id})
        await context.send(
            f"{role.mention} has been set as the muted role.", ephemeral=True
        )

    @_settings.command()
    @is_admin()
    async def logs(
        self,
        context: commands.Context,
        channel: discord.TextChannel = commands.Option(
            None, description="Designated channel to log server events."
        ),
    ):
        """
        Update the guild's logging channel.
        """
        channel: discord.TextChannel = channel or context.channel
        await context.bot.pool.execute(
            "UPDATE guilds SET logs = $1 WHERE guild = $2",
            channel.id,
            context.guild.id,
        )
        await context.send(
            f"Events will now be logged in {channel.mention}", ephemeral=True
        )

    @_settings.group()
    @is_admin()
    async def tickets(self, context: commands.Context):
        pass

    @tickets.command(name="category")
    @is_admin()
    async def tickets_category(
        self,
        context: commands.Context,
        category: discord.CategoryChannel = commands.Option(
            None, description="Category where tickets are created in."
        ),
    ):
        """
        Update which category channel tickets are created in.
        """
        await context.bot.pool.execute(
            "UPDATE guilds SET ticket_category = $1 WHERE guild = $2",
            category.id if category else 0,
            context.guild.id,
        )
        await context.send(
            f"Tickets will now be created in the {category.name}"
            if category
            else "Tickets will now be created in a newly made 'Tickets' category",
            ephemeral=True,
        )

    @tickets.command(name="message")
    @is_admin()
    async def tickets_message(
        self,
        context: commands.Context,
        message: str = commands.Option(
            None,
            description="Message to send when a ticket is created. 2000 character limit.",
        ),
    ):
        message = message[:2000]
        await context.bot.pool.execute(
            "UPDATE guilds SET ticket_message = $1 WHERE guild = $2",
            message,
            context.guild.id,
        )
        await context.send(
            f"Message sent on ticket creation has been set to\n\n{message}"
            if message
            else "No message will be sent on ticket creation.",
            ephemeral=True,
        )


def setup(bot):
    bot.add_cog(Settings(bot))
