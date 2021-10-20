import contextlib
import random
import re
import uuid
from typing import List, Optional, Union

import discord
from discord.ext import commands, menus

from helpers import ViewMenuPages


async def generate_uuid(context: commands.Context) -> int:
    _id = [str(uuid.uuid4()) for _ in range(random.randint(6, 12))]
    new_id = []
    for _uuid in reversed(_id):
        for _ in range(len(_uuid)):
            if len(new_id) == 6:
                generated = int("".join([str(num) for num in new_id]))
                run_again = await check_uuid(context, generated)
                if run_again:
                    await generate_uuid(context)
                else:
                    return generated

            try:
                _int = int(random.choice(_uuid))
                new_id.append(_int)
                new_id.reverse()
            except ValueError:
                continue


async def check_uuid(
    context: commands.Context, _id: int
) -> Optional[Union[list, None]]:
    exists = await context.bot.pool.fetch(
        "SELECT * FROM warns WHERE warning_id = $1", _id
    )
    return exists


### Menus


async def start_menu(
    context: commands.Context,
    source: menus.ListPageSource,
    delete_message_after: bool = False,
    clear_reactions_after: bool = True,
) -> None:
    """
    |coro|

    Method initiates menu instance.
    """
    menu = ViewMenuPages(source=source, clear_reactions_after=clear_reactions_after)
    with contextlib.suppress(AttributeError):
        return await menu.start(context)


class Tags(menus.ListPageSource):
    """
    Returns a pagination of embeds containing information
    relating to guild tags.
    """

    def __init__(self, data: list) -> None:
        super().__init__(data, per_page=10)

    async def format_page(
        self, menu: menus.MenuPages, entries: list
    ) -> Union[str, discord.Embed, dict]:

        embed: discord.Embed = menu.ctx.bot.embed(
            description="\n".join(
                [
                    f"{index}. {entry['tag']} - {entry['creator']}"
                    for index, entry in enumerate(entries, start=1)
                ]
            ),
            color=0x2ECC71,
        )
        embed.set_author(name=str(menu.ctx.guild), icon_url=menu.ctx.guild.icon.url)
        embed.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        return embed


class Mutes(menus.ListPageSource):
    """
    Returns a pagination of embeds containing information
    relating to muted users in a guild.
    """

    def __init__(self, data: list) -> None:
        super().__init__(data, per_page=5)

    async def format_page(
        self, menu: menus.MenuPages, entries: list
    ) -> Union[str, discord.Embed, dict]:

        embed: discord.Embed = menu.ctx.bot.embed(
            description=f"""<@{entries['muted']}> was muted {'' if not entries['reason'] else f'for {entries["reason"][:512]}'} on {discord.utils.format_dt(entries['starts'])}. 
            {f'Ends {discord.utils.format_dt(entries["ends"], "R")}' if entries['ends'] else ''}\n\n""",
            color=0xE67E22,
        )
        embed.set_author(name=str(menu.ctx.guild), icon_url=menu.ctx.guild.icon.url)
        embed.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        return embed


class Warnings(menus.ListPageSource):
    """
    Returns a pagination of embeds containing information
    relating to warnings in a guild.
    """

    def __init__(self, data: list) -> None:
        super().__init__(data, per_page=1)

    async def format_page(
        self, menu: menus.MenuPages, entries: list
    ) -> Union[str, discord.Embed, dict]:

        embed: discord.Embed = menu.ctx.bot.embed(
            description=f"<@{entries['author']}> gave a warning to <@{entries['warned']}> on {discord.utils.format_dt(entries['created'])}.\n\n{entries['warn'][:3900]}",
            color=0xE67E22,
        )
        embed.set_author(name=str(menu.ctx.guild), icon_url=menu.ctx.guild.icon.url)
        embed.set_footer(
            text=f"User ID: {entries['warned']} | Warn ID #{entries['warning_id']} | Warning {menu.current_page + 1}/{self.get_max_pages()}"
        )
        return embed


class HelpMenu(menus.ListPageSource):
    """Returns a pagination of the help command."""

    def __init__(self, data: list) -> None:
        super().__init__(data, per_page=1)

    async def format_page(
        self, menu: menus.MenuPages, entries: list
    ) -> Union[str, discord.Embed, dict]:
        return entries


### Converters


time_regex = re.compile(r"(\d{1,6}(?:[.,]?\d{1,6})?)([smhdwy])")
month_regex = re.compile(
    r"(\d{1,6}(?:[.,]?\d{1,6})?)(\W*((?:)mo|months|month(U?-:))\W*)"
)

time_dict = {
    "hours": 3600,
    "hour": 3600,
    "h": 3600,
    "minutes": 60,
    "minute": 60,
    "m": 60,
    "seconds": 1,
    "second": 1,
    "s": 1,
}

month_dict = {"months": 2628288, "month": 2628288, "mo": 2628288}


class SlowmodeConverter(commands.Converter):
    async def convert(self, context: commands.Context, argument: str) -> int:
        if not argument:
            return 0

        adjusted_argument = argument.lower().replace(" ", "")
        matches = time_regex.findall(adjusted_argument)
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k] * float(v)
            except KeyError:
                raise commands.BadArgument(
                    f"{k} is an invalid unit of time! h/m/s are valid!"
                )
            except ValueError:
                raise commands.BadArgument(f"{v} is not a number!")

        if time > 21600:
            return 21600

        return time


class TimeConverter(commands.Converter):
    async def convert(self, context: commands.Context, argument: str) -> int:
        if not argument:
            return 0

        adjusted_argument = argument.lower().replace(" ", "")
        matches = time_regex.findall(adjusted_argument)
        match = month_regex.findall(adjusted_argument)
        time = 0
        for (
            v,
            k,
        ) in matches:
            try:
                time += time_dict[k] * float(v)
            except KeyError:
                raise commands.BadArgument(
                    f"{k} is an invalid unit of time. y/mo/w/d/h/m/s are valid."
                )
            except ValueError:
                raise commands.BadArgument(f"{v} is not a number.")

        for v, k, i, n in match:
            try:
                time += (month_dict[k] - 60) * float(v)
            except KeyError:
                raise commands.BadArgument(
                    f"{k} is an invalid unit of time. y/mo/w/d/h/m/s are valid."
                )
            except ValueError:
                raise commands.BadArgument(f"{v} is not a number.")

        if time < 1:
            return 0

        return time


class MemberConverter(commands.Converter):
    """
    Attemps to return a Member object through
    local and/or global lookups.
    """

    async def convert(
        self, context: commands.Context, argument: str
    ) -> Optional[discord.Member]:
        cache: dict[int, discord.Member] = context.bot.cache["member"]
        try:
            cached_member = cache.get(int(argument))
            if cached_member:
                return cached_member
        except (ValueError, TypeError):
            pass

        try:
            member = await commands.MemberConverter().convert(context, argument)
            cache.update({member.id: member})
            return member
        except commands.MemberNotFound:
            pass

        try:
            user_id = int(argument)
            member = await context.guild.fetch_member(user_id)
            cache.update({member.id: member})
            return member
        except (discord.NotFound, ValueError):
            pass


class UserConverter(commands.Converter):
    """
    Attemps to return a User object through
    local and/or global lookups.
    """

    async def convert(
        self, context: commands.Context, argument: str
    ) -> Optional[discord.User]:

        try:
            lookup = await commands.UserConverter().convert(context, argument)
            user = await self.find_user(context, lookup.id)
            if user:
                return user
        except commands.UserNotFound:
            pass

    async def find_user(
        self, context: commands.Context, user_id: int
    ) -> Optional[Union[discord.User, None]]:

        cache: dict[int, discord.User] = context.bot.cache["user"]
        cached_user = cache.get(user_id)
        if cached_user:
            return cached_user

        try:
            user: discord.User = await context.bot.fetch_user(user_id)
            if user:
                cache.update({user.id: user})
                return user
        except discord.NotFound:
            pass

        return None


class BannedUserConverter(commands.Converter):
    """
    Attemps to return a User object through
    local and/or global lookups.
    """

    async def convert(
        self, context: commands.Context, argument: str
    ) -> Optional[discord.Object]:

        all_guild_bans: dict[int, dict[str, int]] = context.bot.guild_bans
        guild_ban_entries = all_guild_bans.get(context.guild.id)
        if guild_ban_entries:
            banned_user = guild_ban_entries.get(argument)
            if banned_user:
                return discord.Object(banned_user)

        ban_entries: List[discord.guild.BanEntry] = await context.guild.bans()
        guild_bans = {str(ban.user): ban.user.id for ban in ban_entries}
        context.bot.guild_bans.update({context.guild.id: guild_bans})
        banned_user = guild_bans.get(argument)
        if banned_user:
            return discord.Object(banned_user)
