import difflib
import sys
from typing import List, Mapping, Optional

import discord
from discord.ext import commands


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
        embed: discord.Embed = self.context.bot.embed(color=0x006CCB)
        for cog, commands in mapping.items():
            if cog and len(commands) >= 1:
                embed.add_field(
                    name=cog.qualified_name.title(),
                    value=f"**({len(commands)}) commands**",
                )

        embed.set_thumbnail(url=self.context.bot.avatar)
        await self.context.send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        """
        |coro|

        This method is called when the help command is called with a cog as the argument.
        """
        commands = (
            "\n".join(
                [
                    f"{index}. {self.context.prefix}{command.name.title()}{f' - {command.short_doc}' if len(command.short_doc) > 1 else ''}\n"
                    for index, command in enumerate(cog.get_commands(), start=1)
                ]
            )
            or "None"
        )

        embed: discord.Embed = self.context.bot.embed(
            title=cog.qualified_name.title(),
            description=f"{cog.description}\n\n```{commands}\n```",
            colour=0x006CCB,
        )

        embed.set_thumbnail(url=self.context.bot.avatar)
        embed.set_footer(
            text=f"Type {self.context.prefix}help (command) for more info on a command."
        )

        await self.context.send(embed=embed)

    async def send_group_help(self, group: commands.Group) -> None:
        """
        |coro|

        This method is called when the help command is called with a group as the argument.
        """
        commands = (
            "\n".join(
                [
                    f"{index}. {self.context.prefix}{command}{f' - {command.short_doc}' if len(command.short_doc) > 1 else ''}\n"
                    for index, command in enumerate(group.commands, start=1)
                ]
            )
            or "None"
        )

        embed: discord.Embed = self.context.bot.embed(
            title=f"Parent Command `{group.name}`",
            description=f"```Usage: {self.context.prefix}{group.name} {group.signature}\n\n{commands}```"
            or "No info available.```",
            colour=0x006CCB,
        )

        embed.set_thumbnail(url=self.context.bot.avatar)
        embed.set_footer(
            text=f"Type {self.context.prefix}help (command) for more info on a command."
        )

        await self.context.send(embed=embed)

    async def send_command_help(self, command: commands.Command) -> None:
        """
        |coro|

        This method is called when the help command is called with a command name as the argument.
        """
        aliases = f"Aliase(s): {' • '.join(command.aliases) or 'None'}\n\n"

        parents = (
            "".join([f" {parent} " for parent in command.parents])
            if command.parents
            else ""
        )

        usage = (
            f"Usage: {self.context.prefix}{parents}{command.name} {command.signature}"
        )

        embed: discord.Embed = self.context.bot.embed(
            title=f"Command `{command.name}` info",
            description=f"```{command.short_doc}\n\n{usage}\n\n{aliases}```",
            colour=0x006CCB,
        )

        embed.set_thumbnail(url=self.context.bot.avatar)
        await self.context.send(embed=embed)


class Help(commands.Cog):
    """
    A module to provide users with helpful
    information on the bot.
    """

    def __init__(self, bot) -> None:
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
        admin_invite: str = "https://discord.com/api/oauth2/authorize?client_id=845025665325465630&permissions=8&scope=bot%20applications.commands"
        normal_invite: str = "https://discord.com/api/oauth2/authorize?client_id=845025665325465630&permissions=17883851846&scope=bot%20applications.commands"
        no_perms_invite: str = "https://discord.com/api/oauth2/authorize?client_id=845025665325465630&permissions=0&scope=bot%20applications.commands"

        embed: discord.Embed = context.bot.embed(
            title="Want to invite me to your server?",
            description=f"[Administrator Permissions]({admin_invite})\n[Standard Permissions]({normal_invite})\n[No Permissions]({no_perms_invite})",
            color=0x006CCB,
        )

        await context.send(embed=embed)

    @commands.command()
    async def ping(self, context: commands.Context) -> None:
        """
        Shows current ping.
        """
        embed: discord.Embed = self.bot.embed(
            description=f"**My ping is {round(self.bot.latency * 1000)}ms.**",
            color=0x2ECC71,
        )
        await context.send(embed=embed)

    @commands.command()
    async def uptime(self, context: commands.Context) -> None:
        """
        Shows how long I've been online.
        """
        time = discord.utils.format_dt(context.bot.uptime, "R")
        embed: discord.Embed = self.bot.embed(
            description=f"**Online since {time}.**", color=0x2ECC71
        )
        await context.send(embed=embed)

    @commands.command()
    async def support(self, context: commands.Context) -> None:
        """
        Invite link to the Synico support server.
        """
        embed: discord.Embed = context.bot.embed(
            description=f"[Support Server](https://discord.gg/Xh9Whbrqbj)",
            color=0x2ECC71,
        )
        await context.send(embed=embed)


def setup(bot):
    bot.add_cog(Help(bot))
