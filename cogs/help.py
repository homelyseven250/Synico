from typing import List, Mapping, Optional

import discord
from discord.ext import commands

from main import Bot
from utils import HelpMenu, start_menu


class HelpCommand(commands.HelpCommand):
    """
    Base implementation for help command formatting.
    """

    async def send_bot_help(
        self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]
    ) -> None:
        """
        |coro|

        This method is called when the help command is called with no arguments.
        """
        embeds = []
        embed: discord.Embed = self.context.bot.embed(
            color=0x006CCB,
            description="Welcome to the main help menu for Synico!\n\nUse the buttons below to navigate through the modules.\
                If you are curious on how to run a command then use `/help (command name)`\n\n\
                If you have any suggestions or concerns, let us know by either sending a dm to the owners or using the `/suggest` command.\n\n\
                Thank you for using Synico!",
            timestamp=discord.utils.utcnow(),
        )
        for cog, commands in [
            (cog, commands)
            for cog, commands in mapping.items()
            if cog
            and len(commands) >= 1
            and not cog.qualified_name in ("Developer", "Jishaku")
        ]:
            embeds.append(await self.send_cog_help(cog))

        embed.set_author(
            name="Join the support server!", url="https://discord.gg/Xh9Whbrqbj"
        )
        embed.set_thumbnail(url=self.context.me.display_avatar.url)
        embeds.insert(0, embed)

        await start_menu(self.context, HelpMenu(embeds))

    async def send_cog_help(self, cog: commands.Cog) -> None:
        """
        |coro|

        This method is called when the help command is called with a cog as the argument.
        """

        commands = (
            "\n".join(
                [
                    f"{index}. **/{f'{command.parent} '.title() if command.parents else ''}{command.name.title()}** - {command.short_doc}\n"
                    for index, command in enumerate(cog.walk_commands(), start=1)
                    if command.short_doc
                ]
            )
            or None
        )

        embed: discord.Embed = self.context.bot.embed(
            title=cog.qualified_name.title(),
            description=f"{cog.description}\n\n{commands}\n",
            colour=0x006CCB,
        )

        embed.set_thumbnail(url=self.context.me.display_avatar.url)
        embed.set_footer(text=f"Type /help (command) for more info on a command.")
        return embed

    async def send_group_help(self, group: commands.Group) -> None:
        """
        |coro|

        This method is called when the help command is called with a group as the argument.
        """
        commands = (
            "\n".join(
                [
                    f"{index}. /{command}{f' - {command.short_doc}' if len(command.short_doc) > 1 else ''}\n"
                    for index, command in enumerate(group.commands, start=1)
                ]
            )
            or None
        )

        embed: discord.Embed = self.context.bot.embed(
            title=f"Parent Command `{group.name}`",
            description=f"Usage: /{group.name} {group.signature}\n\n{commands}"
            or "No info available.",
            colour=0x006CCB,
        )

        embed.set_thumbnail(url=self.context.me.display_avatar.url)
        embed.set_footer(text=f"Type /help (command) for more info on a command.")
        await self.context.send(embed=embed, ephemeral=True)

    async def send_command_help(self, command: commands.Command) -> None:
        """
        |coro|

        This method is called when the help command is called with a command name as the argument.
        """
        aliases = f"Aliase(s): {' • '.join(command.aliases) or None}\n\n"

        parents = (
            "".join([f" {parent} " for parent in command.parents])
            if command.parents
            else ""
        )

        usage = f"Usage: /{parents[1:]}{command.name} {command.signature}"

        embed: discord.Embed = self.context.bot.embed(
            title=f"Command `{command.name}` info",
            description=f"{command.short_doc}\n\n{usage}\n\n{aliases}",
            colour=0x006CCB,
        )

        embed.set_thumbnail(url=self.context.me.display_avatar.url)
        await self.context.send(embed=embed, ephemeral=True)


class Help(commands.Cog):
    """
    A module to provide users with helpful
    information on the bot.
    """

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.bot.help_command = HelpCommand(
            command_attrs={"help": "Shows available commands"}
        )

    def cog_unload(self) -> None:
        """
        This method is called before the extension is unloaded
        to reassign the :attr:`help_command` attribute to
        its default value.
        """
        self.bot.help_command = commands.DefaultHelpCommand(
            command_attrs={"help": "Shows available commands"}
        )

    @commands.command()
    async def invite(self, context: commands.Context) -> None:
        """
        Invite links to invite me to your server.
        """
        admin_invite: str = f"https://discord.com/api/oauth2/authorize?client_id={context.me.id}&permissions=8&scope=bot%20applications.commands"
        normal_invite: str = f"https://discord.com/api/oauth2/authorize?client_id={context.me.id}&permissions=398324002038&scope=bot%20applications.commands"
        no_perms_invite: str = f"https://discord.com/api/oauth2/authorize?client_id={context.me.id}&permissions=0&scope=bot%20applications.commands"

        embed: discord.Embed = context.bot.embed(
            title="Want to invite me to your server?",
            description=f"[Administrator Permissions]({admin_invite})\n[Standard Permissions]({normal_invite})\n[No Permissions]({no_perms_invite})",
            color=0x006CCB,
        )

        await context.send(embed=embed, ephemeral=True)

    @commands.command()
    async def support(self, context: commands.Context) -> None:
        """
        Invite link to the Synico support server.
        """
        embed: discord.Embed = context.bot.embed(
            description=f"[Support Server](https://discord.gg/Xh9Whbrqbj)",
            color=0x2ECC71,
        )
        await context.send(embed=embed, ephemeral=True)

    @commands.command()
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def suggest(
        self,
        context: commands.Context,
        suggestion: str = commands.Option(description="A suggestion for the bot."),
    ):
        """
        Make a suggestion or report a bug to the developers.
        """
        embed: discord.Embed = context.bot.embed(
            title=f"Suggestion from {context.author}!",
            description=suggestion,
            color=0x2ECC71,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name=str(context.author), icon_url=context.author.display_avatar.url
        )
        channel: discord.TextChannel = context.bot.get_channel(858760527827042317)

        try:
            await channel.send(
                ", ".join([f"<@{_id}>" for _id in context.bot.owner_ids]),
                embed=embed,
            )
            await context.send("Suggestion submitted.", ephemeral=True)
        except (discord.HTTPException, discord.Forbidden, AttributeError):
            await context.send(
                "Suggestion failed. Please try again later.", ephemeral=True
            )


def setup(bot: Bot):
    bot.add_cog(Help(bot))
