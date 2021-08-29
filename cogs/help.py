import difflib
import sys
from typing import List, Mapping, Optional

import discord
from discord.ext import commands


class HelpCommand(commands.HelpCommand):
    """
    Base implementation for help command formatting.
    """

    async def command_not_found(self, string: str):
        """
        |coro|

        A method called when a command is not found in the help command.
        """
        command_list = [cmd.name for cmd in self.context.bot.commands]

        matches = difflib.get_close_matches(string, command_list)
        if not matches:
            embed = self.context.bot.embed(
                description=f"```diff\n- Command '{string}' does not exist.\n```",
                colour=0x006CCB,
            )
            await self.context.send(embed=embed)

        else:
            top = "\n".join(
                [
                    f"{index}. {match}"
                    for index, match, in enumerate(matches[:3], start=1)
                ]
            )

            embed = self.context.bot.embed(
                description=f"```Command '{string}' does not exist. Did you mean:\n{top}\n```",
                colour=0x006CCB,
            )
            await self.context.send(embed=embed)

    async def send_bot_help(
        self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]
    ):
        """
        |coro|

        This method is called when the help command is called with no arguments.
        """
        embed = self.context.bot.embed(color=0x006CCB)
        for cog, commands in mapping.items():
            if cog and len(commands) >= 1:
                embed.add_field(
                    name=cog.qualified_name.title(),
                    value=f"**({len(commands)}) commands**",
                )

        embed.set_thumbnail(url=self.context.me.avatar.url)
        await self.context.send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog):
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

        embed = self.context.bot.embed(
            title=cog.qualified_name.title(),
            description=f"{cog.description}\n\n```{commands}\n```",
            colour=0x006CCB,
        )

        embed.set_thumbnail(url=self.context.me.avatar.url)
        embed.set_footer(
            text=f"Type {self.context.prefix}help (command) for more info on a command."
        )

        await self.context.send(embed=embed)

    async def send_group_help(self, group: commands.Group):
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

        embed = self.context.bot.embed(
            title=f"Parent Command `{group.name}`",
            description=f"```Usage: {self.context.prefix}{group.name} {group.signature}\n\n{commands}```"
            or "No info available.```",
            colour=0x006CCB,
        )

        embed.set_thumbnail(url=self.context.me.avatar.url)
        embed.set_footer(
            text=f"Type {self.context.prefix}help (command) for more info on a command."
        )

        await self.context.send(embed=embed)

    async def send_command_help(self, command: commands.Command):
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

        embed = self.context.bot.embed(
            title=f"Command `{command.name}` info",
            description=f"```{command.short_doc}\n\n{usage}\n\n{aliases}```",
            colour=0x006CCB,
        )

        embed.set_thumbnail(url=self.context.me.avatar.url)
        await self.context.send(embed=embed)


class Help(commands.Cog):
    """
    A module to provide users with helpful
    information on the bot.
    """

    def __init__(self, bot):
        self.bot = bot
        self.bot.help_command = HelpCommand(command_attrs=dict(hidden=True))

    def cog_unload(self):
        """
        This method is called before the extension is unloaded
        to reassign the :attr:`help_command` attribute to
        its default value.
        """
        self.bot.help_command = commands.DefaultHelpCommand()

    @commands.command()
    async def invite(self, context: commands.Context):
        """
        Invite links to invite me to your server.
        """
        admin_invite: str = (
            context.bot.config["INVITE"]["admin"] + "%20applications.commands"
        )
        normal_invite: str = (
            context.bot.config["INVITE"]["normal"] + "%20applications.commands"
        )
        no_perms_invite: str = (
            context.bot.config["INVITE"]["none"] + "%20applications.commands"
        )

        embed = context.bot.embed(
            title="Want to invite me to your server?",
            description=f"[Administrator Permissions]({admin_invite})\n[Standard Permissions]({normal_invite})\n[No Permissions]({no_perms_invite})",
            color=0x006CCB,
        )

        await context.reply(embed=embed)

    @commands.command()
    async def ping(self, context: commands.Context):
        """
        Shows current ping.
        """
        embed = self.bot.embed(
            description=f"**My ping is {round(self.bot.latency * 1000)}ms.**",
            color=0x2ECC71,
        )
        await context.send(embed=embed)

    @commands.command()
    async def uptime(self, context: commands.Context):
        """
        Shows how long I've been online.
        """
        time = discord.utils.format_dt(context.bot.uptime, "R")
        embed = self.bot.embed(description=f"**Online since {time}.**", color=0x2ECC71)
        await context.send(embed=embed)

    @commands.command()
    async def version(self, context: commands.Context):
        """
        Display current version of Python and d.py.
        """
        embed = context.bot.embed(
            description=f"**Python Version: {sys.version[:6]} - {sys.version_info.releaselevel}\nDiscord.py Version: {discord.__version__} - {discord.version_info.releaselevel}**",
            color=0x2ECC71,
        )
        await context.send(embed=embed)


def setup(bot):
    bot.add_cog(Help(bot))
