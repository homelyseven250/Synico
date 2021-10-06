from datetime import datetime

import discord
from discord.ext import commands
from utils import NotAdmin, NotGuildOwner, NotMod


class Errors(commands.Cog):
    """
    A class that inherits from
    :class:`commands.Cog` with the
    intent to catch and handle
    exception output.
    """

    def __init__(self, bot) -> None:
        self.bot = bot

    # Need to to decide on error type before adding typehint
    async def format_error(self, context: commands.Context, error) -> None:
        """
        |coro|

        A method to escape markdown within a string
        before sending error output.
        """
        formatted = discord.utils.escape_markdown(str(error))
        await context.send(content=f"**⚠️ | {formatted}**", ephemeral=True)

    @commands.Cog.listener()
    async def on_command_error(self, context: commands.Context, error):
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
            await context.send(
                f"Conversion failed in [{error.converter}]: {error.__cause__}"
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
            await context.send(error)

        elif isinstance(error, commands.BotMissingPermissions):
            await context.send(context.me.mention + error.args[0][3:])

        elif isinstance(error, commands.MissingRole):
            await context.send(error)

        elif isinstance(error, commands.BotMissingRole):
            await context.send(context.me.mention + error[3:])

        elif isinstance(error, commands.MissingAnyRole):
            await context.send(error)

        elif isinstance(error, commands.BotMissingAnyRole):
            await context.send(context.me.mention + error[3:])

        elif isinstance(error, commands.NSFWChannelRequired):
            await context.send(
                f"{context.channel} needs to be NSFW to run {context.prefix}{context.invoked_with}"
            )

        elif isinstance(error, commands.DisabledCommand):
            return

        elif isinstance(error, commands.CommandOnCooldown):
            duration = discord.utils.format_dt(
                datetime.fromtimestamp(error.retry_after).timestamp, "R"
            )
            await context.send(
                f"{context.prefix}{context.invoked_with} is on cooldown. Try again in {duration}."
            )

        elif isinstance(error, commands.MaxConcurrencyReached):
            await context.send(
                f"{context.prefix}{context.invoked_with} can be used {error.args[0][56:-14].replace('guild', 'server')}."
            )

        elif isinstance(error, NotMod):
            await context.send(
                f"Only moderators can use the command {context.prefix}{context.invoked_with}"
            )

        elif isinstance(error, NotAdmin):
            await context.send(
                f"Only admins can use the command {context.prefix}{context.invoked_with}"
            )

        elif isinstance(error, NotGuildOwner):
            await context.send(
                f"Only the owner of {context.guild} can use the command {context.prefix}{context.invoked_with}"
            )

        else:
            print(f"Unhandled exception in command [{context.command}]:", error)


def setup(bot):
    bot.add_cog(Errors(bot))
