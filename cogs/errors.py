import sys
import traceback
from datetime import datetime
from typing import List, Union

import discord
from discord.ext import commands


class NotMod(commands.CheckFailure):
    pass


class NotAdmin(commands.CheckFailure):
    pass


class NotGuildOwner(commands.CheckFailure):
    pass


def has_admin(context: commands.Context) -> bool:
    """
    Returns whether a user has administrative power.
    """
    permissions = [
        k
        for k, v in dict(
            discord.Permissions(context.author.guild_permissions.value)
        ).items()
        if v
    ]
    if "administrator" in permissions:
        return True

    return False


def guild_owner() -> commands.check:
    """
    A custom decorator that validates
    whether a user is the server owner.
    """

    async def predicate(context: commands.Context) -> Union[bool, Exception]:
        if context.author.id == context.guild.owner_id:
            return True

        raise NotGuildOwner()

    return commands.check(predicate)


def guild_bot_owner() -> commands.check:
    """
    A custom decorator that validates whether the user
    is the server owner or bot owner.
    """

    async def predicate(context: commands.Context) -> Union[bool, Exception]:
        if (
            context.author.id in context.bot.owner_ids
            or context.author.id == context.guild.owner_id
        ):
            return True

        raise NotGuildOwner()

    return commands.check(predicate)


def is_admin() -> commands.check:
    """
    A custom decorator that validates
    whether a user has higher level authorization.
    """

    async def predicate(context: commands.Context) -> Union[bool, Exception]:
        if (
            context.author.id == context.guild.owner_id
            or context.guild.get_role(
                context.bot.admins.get(context.guild.id).get("admin")
            )
            in context.author.roles
            or has_admin(context)
        ):
            return True

        raise NotAdmin()

    return commands.check(predicate)


def is_mod() -> commands.check:
    """
    A custom decorator that validates
    whether a user has lower level authorization.
    """

    async def predicate(context: commands.Context) -> Union[bool, Exception]:
        if (
            context.author.id == context.guild.owner_id
            or context.guild.get_role(
                context.bot.admins.get(context.guild.id).get("mod")
            )
            in context.author.roles
            or context.guild.get_role(
                context.bot.admins.get(context.guild.id).get("admin")
            )
            in context.author.roles
            or has_admin(context)
        ):
            return True

        raise NotMod()

    return commands.check(predicate)


def tag_perms(context: commands.Context, owner: int) -> bool:
    """
    This method validates permission of command author when
    editing/deleting tags.
    """
    if (
        context.author.id == context.guild.owner_id
        or context.guild.get_role(context.bot.admins.get(context.guild.id).get("mod"))
        in context.author.roles
        or context.guild.get_role(context.bot.admins.get(context.guild.id).get("admin"))
        in context.author.roles
        or has_admin(context)
        or context.author.id == owner.id
    ):

        return True

    return False


class Errors(commands.Cog):
    """
    A class that inherits from
    :class:`commands.Cog` with the
    intent to catch and handle
    exception output.
    """

    def __init__(self, bot) -> None:
        self.bot = bot

    async def format_error(self, context: commands.Context, error: str) -> None:
        """
        |coro|

        A method to escape markdown within a string
        before sending error output.
        """
        formatted = discord.utils.escape_markdown(str(error))
        await context.send(content=f"**⚠️ | {formatted}**", ephemeral=True)

    @commands.Cog.listener()
    async def on_command_error(self, context: commands.Context, error: Exception):
        """
        An event that is fired when an exception
        occurs.
        """
        if hasattr(context.command, "on_error"):
            return

        if context.cog:
            cog = context.cog
            if cog._get_overridden_method(cog.cog_command_error):
                return

        error = getattr(error, "original", error)

        if isinstance(error, commands.ConversionError):
            await self.format_error(
                context, f"Conversion failed in [{error.converter}]: {error.__cause__}"
            )

        elif isinstance(error, commands.MissingRequiredArgument):
            await self.format_error(context, error)

        elif isinstance(error, commands.TooManyArguments):
            await self.format_error(
                context,
                f"{context.command} received too many inputs. \
                \nProper usage: {context.prefix}{context.command.signature}",
            )

        elif isinstance(error, commands.MessageNotFound):
            await self.format_error(context, error)

        elif isinstance(error, commands.MemberNotFound):
            await self.format_error(context, f"Could not find member: {error.argument}")

        elif isinstance(error, commands.GuildNotFound):
            await self.format_error(context, f"Could not find server: {error.argument}")

        elif isinstance(error, commands.UserNotFound):
            await self.format_error(context, f"Could not find user: {error.argument}")

        elif isinstance(error, commands.ChannelNotFound):
            await self.format_error(
                context, f"Could not find channel: {error.argument}"
            )

        elif isinstance(error, commands.ChannelNotReadable):
            await self.format_error(
                context, f"Unable to access channel: {error.argument.mention}"
            )

        elif isinstance(error, commands.BadColourArgument):
            await self.format_error(context, f"Invalid color: {error.argument}")

        elif isinstance(error, commands.RoleNotFound):
            await self.format_error(context, f"Could not find role: {error.argument}")

        elif isinstance(error, commands.BadInviteArgument):
            await self.format_error(
                context, f"Invite <{error.argument}> is either invalid or has expired."
            )

        elif isinstance(error, commands.EmojiNotFound):
            await self.format_error(context, f"Could not find emoji: {error.argument}")

        elif isinstance(error, commands.GuildStickerNotFound):
            await self.format_error(
                context, f"Could not find sticker: {error.argument}"
            )

        elif isinstance(error, commands.PartialEmojiConversionFailure):
            await self.format_error(
                context, f"Failed to convert {error.argument} into a Partial Emoji."
            )

        elif isinstance(error, commands.BadBoolArgument):
            await self.format_error(
                context,
                f"{error.argument} is not a valid option. Either True or False.",
            )

        elif isinstance(error, commands.ThreadNotFound):
            await self.format_error(context, f"Could not find thread: {error.argument}")

        elif isinstance(error, commands.BadFlagArgument):
            try:
                name = error.flag.annotation.__name__
            except AttributeError:
                name = error.flag.annotation.__class__.__name__

            await self.format_error(
                context, f"Could not convert flag {error.flag.name} to {name}"
            )

        elif isinstance(error, commands.MissingFlagArgument):
            await self.format_error(
                context, f"Input missing for flag {error.flag.name}"
            )

        elif isinstance(error, commands.TooManyFlags):
            await self.format_error(
                context,
                f"{error.flag.name} accepts {error.flag.max_args} values\
                but received {len(error.values)} values.",
            )

        elif isinstance(error, commands.MissingRequiredFlag):
            await self.format_error(
                context, f"Flag {error.flag.name} did not receive an input."
            )

        elif isinstance(error, commands.BadUnionArgument):
            await self.format_error(context, error)

        elif isinstance(error, commands.BadLiteralArgument):
            await self.format_error(context, error)

        elif isinstance(error, commands.UnexpectedQuoteError):
            await self.format_error(context, error)

        elif isinstance(error, commands.InvalidEndOfQuotedStringError):
            await self.format_error(context, error)

        elif isinstance(error, commands.ExpectedClosingQuoteError):
            await self.format_error(context, error)

        elif isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, commands.CheckAnyFailure):
            await self.format_error(context, error)

        elif isinstance(error, commands.PrivateMessageOnly):
            await self.format_error(context, error)

        elif isinstance(error, commands.NoPrivateMessage):
            await self.format_error(context, error)

        elif isinstance(error, commands.NotOwner):
            return

        elif isinstance(error, commands.MissingPermissions):
            await self.format_error(context, error)

        elif isinstance(error, commands.BotMissingPermissions):
            await self.format_error(context, context.me.mention + error.args[0][3:])

        elif isinstance(error, commands.MissingRole):
            await self.format_error(context, error)

        elif isinstance(error, commands.BotMissingRole):
            await self.format_error(context, context.me.mention + error[3:])

        elif isinstance(error, commands.MissingAnyRole):
            await self.format_error(context, error)

        elif isinstance(error, commands.BotMissingAnyRole):
            await self.format_error(context, context.me.mention + error[3:])

        elif isinstance(error, commands.NSFWChannelRequired):
            await self.format_error(
                context,
                f"{context.channel} needs to be NSFW to run {context.prefix}{context.invoked_with}",
            )

        elif isinstance(error, commands.DisabledCommand):
            return

        elif isinstance(error, commands.CommandOnCooldown):
            duration = discord.utils.format_dt(
                datetime.fromtimestamp(error.retry_after).timestamp, "R"
            )
            await self.format_error(
                context,
                f"{context.prefix}{context.invoked_with} is on cooldown. Try again in {duration}.",
            )

        elif isinstance(error, commands.MaxConcurrencyReached):
            await self.format_error(
                context,
                f"{context.prefix}{context.invoked_with} can be used {error.args[0][56:-14].replace('guild', 'server')}.",
            )

        elif isinstance(error, NotMod):
            await self.format_error(
                context,
                f"Only mods can use the command {context.prefix}{context.invoked_with}",
            )

        elif isinstance(error, NotAdmin):
            await self.format_error(
                context,
                f"Only admins can use the command {context.prefix}{context.invoked_with}",
            )

        elif isinstance(error, NotGuildOwner):
            await self.format_error(
                context,
                f"Only the owner of {context.guild} can use the command {context.prefix}{context.invoked_with}",
            )

        else:
            unhandled_error: List[str] = traceback.format_exception(
                etype=type(error), value=error, tb=error.__traceback__
            )
            channel: discord.TextChannel = context.bot.get_channel(899515548222754908)
            embed: discord.Embed = context.bot.embed(
                title=f"Unhandled exception in command [{context.command}]:",
                description="".join(unhandled_error),
                color=0x2ECC71,
                timestamp=discord.utils.utcnow(),
            )
            embed.set_author(
                name=str(context.author), icon_url=context.author.display_avatar
            )
            embed.set_footer(text=(context.guild), icon_url=context.guild.icon.url)
            await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Errors(bot))
