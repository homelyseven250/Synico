import asyncio
import discord
from main import Bot
from discord.ext import commands

from utils import generate_uuid
from cogs.errors import is_mod


class Confirm(discord.ui.View):
    def __init__(self, channel_id: int, ticket_id: int):
        self.channel_id = channel_id
        self.ticket_id = ticket_id
        super().__init__(timeout=None)
        button = discord.ui.Button(
            label="Close Ticket",
            style=discord.ButtonStyle.red,
            custom_id=str(self.ticket_id),
        )
        button.callback = self.close_ticket
        self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.channel_id == interaction.channel_id:
            return True

        return False

    async def close_ticket(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Ticket has been closed by {interaction.user}, deleting ticket."
        )
        await asyncio.sleep(5)
        await interaction.channel.delete(
            reason=f"Ticket by {interaction.channel.name} ({self.ticket_id}) was closed by {interaction.user}"
        )
        self.stop()


class Tickets(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()
        self.open_tickets = {
            author: {
                "guild": guild,
                "channel": channel,
                "message": message,
                "ticket": ticket,
            }
            for author, guild, channel, message, ticket in await self.bot.pool.fetch(
                "SELECT ticket_author, guild, ticket_channel, message_id, ticket_id FROM tickets"
            )
        }

        for author in iter(self.open_tickets):
            author_ticket = self.open_tickets[author]
            guild, channel, message, ticket = (
                author_ticket["guild"],
                author_ticket["channel"],
                author_ticket["message"],
                author_ticket["ticket"],
            )
            if channel and message:
                _channel = self.bot.get_channel(channel)
                if not _channel:
                    await self.bot.pool.execute(
                        "DELETE FROM tickets WHERE guild = $1 AND ticket_channel = $2",
                        guild,
                        channel,
                    )
                    continue

                self.bot.add_view(Confirm(channel, ticket), message_id=message)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if isinstance(channel, discord.TextChannel):
            await self.bot.pool.execute(
                "DELETE FROM tickets WHERE guild = $1 AND ticket_channel = $2",
                channel.guild.id,
                channel.id,
            )

        elif isinstance(channel, discord.CategoryChannel):
            for author in iter(self.open_tickets):
                author_ticket = self.open_tickets[author]
                channel_id, message = (
                    author_ticket.get("channel"),
                    author_ticket.get("message"),
                )
                if channel_id and message:
                    _channel = self.bot.get_channel(channel)
                    if not _channel:
                        await self.bot.pool.execute(
                            "DELETE FROM tickets WHERE guild = $1 AND ticket_channel = $2",
                            channel.guild.id,
                            channel_id,
                        )
                        continue

    @commands.group()
    async def ticket(self, context: commands.Context):
        pass

    @ticket.command(name="create")
    async def ticket_create(self, context: commands.Context):
        """
        Create a ticket.
        """
        _open_ticket: int = await self.bot.pool.fetchval(
            "SELECT ticket_channel FROM tickets WHERE guild = $1 AND ticket_author = $2",
            context.guild.id,
            context.author.id,
        )
        if _open_ticket:
            await context.send(
                f"Please close your previous ticket in <#{_open_ticket}> before opening a new one.",
                ephemeral=True,
            )
            return

        category_id: int = await self.bot.pool.fetchval(
            "SELECT ticket_category FROM guilds WHERE guild = $1", context.guild.id
        )
        category = context.guild.get_channel(category_id)
        role_overwrites = {
            role: discord.PermissionOverwrite(read_messages=False)
            for role in context.guild.roles
            if role.id != self.bot.admins.get("admin", 0)
            or role.id != self.bot.admins.get("mod", 0)
            or not any(
                role.permissions.manage_messages,
                role.permissions.administrator,
                role.permissions.kick_members,
                role.permissions.ban_members,
            )
            or not context.guild.self_role
        }
        bot_role_overwrites = {
            context.guild.self_role: discord.PermissionOverwrite(view_channel=True)
        }
        member_overwrites = {
            context.guild.me: discord.PermissionOverwrite(
                read_messages=True, view_channel=True
            ),
            context.author: discord.PermissionOverwrite(read_messages=True),
        }
        overwrites = {**member_overwrites, **role_overwrites, **bot_role_overwrites}
        ticket_id = await generate_uuid(context)
        if category:
            channel = await category.create_text_channel(
                name=f"{context.author}"[:100],
                overwrites=overwrites,
                reason=f"Ticket created by {context.author}",
            )

            embed: discord.Embed = context.bot.embed(
                description=f"Ticket created by {context.author} on {discord.utils.format_dt(discord.utils.utcnow())}\n\nClose ticket by either pressing the button below or using {context.prefix or '/'}ticket close {ticket_id}",
                color=0x2ECC71,
            )
            embed.set_footer(text=f"Ticket ID: {ticket_id}")
            view = Confirm(channel.id, ticket_id)
            message = await channel.send(embed=embed, view=view)

            await context.bot.pool.execute(
                "INSERT INTO tickets VALUES ($1, $2, $3, $4, $5)",
                context.guild.id,
                ticket_id,
                context.author.id,
                channel.id,
                message.id,
            )

            await context.send(f"View ticket in {channel.mention}", ephemeral=True)

        else:
            category = await context.guild.create_category(
                name="Tickets",
                overwrites=overwrites,
                reason="Automatic ticket category creation.",
            )
            await context.bot.pool.execute(
                "UPDATE guilds SET ticket_category = $1 WHERE guild = $2",
                category.id,
                context.guild.id,
            )

            channel = await category.create_text_channel(
                name=f"{context.author}"[:100],
                overwrites=overwrites,
                reason=f"Ticket created by {context.author}",
            )
            embed: discord.Embed = context.bot.embed(
                description=f"Ticket created by {context.author} on {discord.utils.format_dt(discord.utils.utcnow())}\n\nClose ticket by either pressing the button below or using {context.prefix or '/'}ticket close {ticket_id}",
                color=0x2ECC71,
            )
            embed.set_footer(text=f"Ticket ID: {ticket_id}")
            view = Confirm(channel.id, ticket_id)
            message = await channel.send(embed=embed, view=view)

            await context.bot.pool.execute(
                "INSERT INTO tickets VALUES ($1, $2, $3, $4, $5)",
                context.guild.id,
                ticket_id,
                context.author.id,
                channel.id,
                message.id,
            )
            await context.send(f"View ticket in {channel.mention}", ephemeral=True)

    @ticket.command(name="close")
    @is_mod()
    async def ticket_close(
        self,
        context: commands.Context,
        id: int = commands.Option(description="ID of ticket."),
    ):
        """
        Close a ticket.
        """
        ticket = await self.bot.pool.fetch(
            "SELECT * FROM tickets WHERE guild = $1 AND ticket_id = $2",
            context.guild.id,
            id,
        )
        if ticket:
            ticket = ticket[0]
            ticket_id = ticket["ticket_id"]
            channel_id = ticket["ticket_channel"]
            channel = context.guild.get_channel(channel_id)
            if channel:
                await self.bot.pool.execute(
                    "DELETE FROM tickets WHERE ticket_channel = $1", channel_id
                )
                await context.send(f"Ticket {id} has been deleted.", ephemeral=True)
                await channel.delete(
                    reason=f"Ticket by {channel.name} ({ticket_id}) was closed by {context.author}"
                )

                return

            await self.bot.pool.execute(
                "DELETE FROM tickets WHERE ticket_channel = $1", channel_id
            )
            await context.send(f"Ticket {id} has been deleted.", ephemeral=True)
            return

        await context.send(f"Could not find ticket with ID {id}.", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(Tickets(bot))
