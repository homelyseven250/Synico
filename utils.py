import inspect
import os
from concurrent.futures import ThreadPoolExecutor

import discord
from discord.ext import commands, menus


class NotMod(commands.CheckFailure):
    pass


class NotAdmin(commands.CheckFailure):
    pass


class NotGuildOwner(commands.CheckFailure):
    pass


class UserConverter(commands.Converter):
    """
    Attemps to return a Member or User object through
    local and/or global lookups.
    """

    async def convert(self, context: commands.Context, argument: str):
        cache: dict = context.bot.cache["member"]

        try:
            member = await commands.MemberConverter().convert(context, argument)
            cache.update({member.id: member})
            return member
        except commands.MemberNotFound:
            pass

        try:
            user = await commands.UserConverter().convert(context, argument)
            cache.update({user.id: user})
            return user
        except commands.UserNotFound:
            pass

        try:
            user_id = int(argument)
            member = await context.guild.fetch_member(user_id)
            cache.update({member.id: member})
            return member
        except commands.MemberNotFound:
            pass

        raise commands.MemberNotFound(argument)


class RoleConverter(commands.Converter):
    """
    Attempts to find a guild role case-insensitively.
    """

    async def convert(self, context, argument):
        try:
            return await commands.RoleConverter().convert(context, argument)
        except commands.RoleNotFound:

            def check(role):
                return (
                    role.name.lower() == argument.lower()
                    or str(role).lower() == argument.lower()
                    or str(role.id) == argument
                )

            if found := discord.utils.find(check, context.guild.roles):
                return found


class SourceReader(commands.Converter):
    """
    Retrieves the source information within a specific
    segment of code or an entire file.
    """

    async def convert(self, context: commands.Context, argument: str):
        cmd = await self.find_command(context, argument)
        if not cmd:
            if argument == "config.ini":
                raise commands.BadArgument("Not accessible.")

            with ThreadPoolExecutor() as pool:
                file = await context.bot.loop.run_in_executor(
                    pool, self.file_search, argument
                )
                if not file:
                    raise commands.BadArgument(
                        f"Could not find a file named **{argument}**"
                    )

                result = await context.bot.loop.run_in_executor(
                    pool, self.file_copy, file
                )

            page_source = StringPagination(result.pages)
            menu = menus.MenuPages(page_source, delete_message_after=True)
            return menu

        with ThreadPoolExecutor() as pool:
            result = await context.bot.loop.run_in_executor(pool, self.cmd_copy, cmd)

        page_source = StringPagination(result.pages)
        menu = menus.MenuPages(page_source, delete_message_after=True)

        return menu

    async def find_command(self, context, argument):
        """
        |coro|

        Method attempts to determine whether user input is for a command
        or for a file.
        """
        command = context.bot.get_command(argument)
        if not command:
            return False

        return command

    def cmd_copy(self, cmd):
        """
        Returns a pagination class containing the source
        lines of a specific segment of code.
        """
        source_code, _ = inspect.getsourcelines(cmd.callback)
        page = commands.Paginator(prefix="```py\n", linesep="", max_size=1998)
        for line in source_code:
            page.add_line(line)

        return page

    def file_copy(self, file: str):
        """
        Creates a pagination class containing the source lines
        of a file.
        """
        page = commands.Paginator(prefix="```py\n", linesep="", max_size=1998)
        with open(file, "r", encoding="utf-8") as source:
            lines = source.readlines()
            for line in lines:
                page.add_line(line)

        return page

    def file_search(self, file: str = None):
        """
        Returns absolute path to file being searched for.
        """
        if file:
            for dirpath, _, filename in os.walk(os.path.abspath(".")):
                for files in filename:
                    if file in files:
                        return f"{dirpath}{os.path.sep}{files}"

        return None


async def start_menu(
    context: commands.Context,
    source: menus.ListPageSource,
    delete_message_after: bool = True,
):
    """
    |coro|

    Method initiates menu instance.
    """
    menu = menus.MenuPages(source=source, delete_message_after=delete_message_after)
    return await menu.start(context)


class StringPagination(menus.ListPageSource):
    """
    Returns a stringed pagination to allow for basic
    codeblock use without embedding.
    """

    def __init__(self, data):
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        return entries + f"\n\nPage {menu.current_page + 1}/{self.get_max_pages()}"


class Tags(menus.ListPageSource):
    """
    Returns a pagination of embeds containing information
    relating to guild tags.
    """

    def __init__(self, data):
        super().__init__(data, per_page=10)

    async def format_page(self, menu, entries):
        embed = discord.Embed(
            description="\n".join(
                [f"{index}. {tag[5]}" for index, tag in enumerate(entries, start=1)]
            ),
            color=0x2ECC71,
        )
        embed.set_author(
            name=str(menu.context.guild), icon_url=menu.context.guild.icon.url
        )
        embed.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        return embed


class Mutes(menus.ListPageSource):
    """
    Returns a pagination of embeds containing information
    relating to muted users in a guild.
    """

    def __init__(self, data):
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        remaining = discord.utils.format_dt(entries[2], "R")
        issued = discord.utils.format_dt(entries[3])

        embed = discord.Embed(
            description=f"**<@{entries[1]}> was muted for {entries[4]} on {issued} and will be unmuted in {remaining}.**",
            color=0xE67E22,
        )
        embed.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        return embed


class Warnings(menus.ListPageSource):
    """
    Returns a pagination of embeds containing information
    relating to warnings in a guild.
    """

    def __init__(self, data):
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):

        embed = discord.Embed(
            title=f"Warning {menu.current_page + 1}/{self.get_max_pages()}",
            description=f"**<@{entries[2]}> issued a warning to <@{entries[0]}> on {discord.utils.format_dt(entries[5])}.\n\nReason: {entries[1]}**",
            color=0xE67E22,
        )
        embed.set_footer(text=f"User ID: {entries[0]} | Warn ID #{entries[4]}")
        return embed


class Streamers(menus.ListPageSource):
    """
    Returns a pagination of embeds containing information
    relating to followed Twitch streamers in a guild.
    """

    def __init__(self, data):
        super().__init__(data, per_page=15)

    async def format_page(self, menu, entries):

        embed = discord.Embed(
            title=f"Following {len(entries)} Twitch channels",
            description="\n".join(
                [
                    f"**{index}. [{streamer[0]}](https://www.twitch.tv/{streamer[0]})**"
                    for index, streamer in enumerate(entries, start=1)
                ]
            ),
            color=0x2ECC71,
        )
        embed.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        return embed


def has_admin(context):
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


def guild_owner():
    """
    A custom decorator that validates
    whether a user is the server owner.
    """

    async def predicate(context):
        if context.author.id == context.guild.owner_id:
            return True

        raise NotGuildOwner()

    return commands.check(predicate)


def guild_bot_owner():
    """
    A custom decorator that validates whether the user
    is the server owner or bot owner.
    """

    async def predicate(context: commands.Context):
        if (
            context.author.id in context.bot.owner_ids
            or context.author.id == context.guild.owner_id
        ):
            return True

        raise NotGuildOwner()

    return commands.check(predicate)


def is_admin():
    """
    A custom decorator that validates
    whether a user has higher level authorization.
    """

    async def predicate(context):
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


def is_mod():
    """
    A custom decorator that validates
    whether a user has lower level authorization.
    """

    async def predicate(context):
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


def tag_perms(context: commands.Context, owner: int):
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
