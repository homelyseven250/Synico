import asyncio
import datetime
from typing import List, Optional, Union

import discord
from discord.ext import commands, tasks


class Events(commands.Cog):
    """
    A module that receives and handles
    all incoming events.
    """

    def __init__(self, bot):
        self.bot = bot
        self.embeds = {}
        self.logs = {}
        self.webhooks = {}

        loop: asyncio.AbstractEventLoop = self.bot.loop

        loop.create_task(self.__ainit__())

    async def __ainit__(self) -> None:
        """
        |coro|

        An asynchronous version of :method:`__init__`
        to access coroutines.
        """
        await self.dispatch_events.start()

    def cog_unload(self) -> None:
        """
        This method is called before the extension is unloaded
        to allow for the running task loop to gracefully
        close after finishing final iteration.
        """
        self.dispatch_events.stop()
        super().cog_unload()

    @tasks.loop(seconds=10, reconnect=True)
    async def dispatch_events(self) -> None:
        """
        |coro|

        A running task loop that repeats after each iteration
        asynchronously to to check if a server has any
        pending outgoing events and dispatches them.
        """
        if len(self.embeds) >= 1:
            for guild in iter(self.embeds):
                if len(self.embeds[guild]["embeds"]) > 0:
                    webhook: discord.Webhook = self.embeds[guild]["webhook"]
                    embeds: List[discord.Embed] = self.embeds[guild]["embeds"][:10]
                    if webhook:
                        try:
                            await webhook.send(
                                embeds=embeds, avatar_url=self.bot.user.avatar.url
                            )
                        except discord.HTTPException:
                            for embed in embeds:
                                await webhook.send(
                                    embed=embed, avatar_url=self.bot.user.avatar.url
                                )
                                await asyncio.sleep(1)

                        del self.embeds[guild]["embeds"][:10]

    async def prepare_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        """
        |coro|

        Returns a `Webhook` for dispatching events.
        """
        if self.webhooks.get(channel.guild.id):
            return discord.Webhook.from_url(
                self.webhooks[channel.guild.id], session=self.bot.cs
            )

        else:
            webhooks = await channel.webhooks()
            if webhooks:
                for webhook in webhooks:
                    if webhook.token:
                        return webhook

                webhook = await channel.create_webhook(name="Synico")
                self.webhooks[channel.guild.id] = webhook.url
                return webhook

    async def log_channel(self, guild: int) -> Optional[discord.TextChannel]:
        """
        |coro|

        Either returns a `TextChannel` or `None` if a server has a
        channel setup for logging events.
        """
        if not self.logs.get(guild):
            channel: Optional[int] = await self.bot.pool.fetchval(
                "SELECT log FROM guilds WHERE guild = $1", guild
            )
            if channel:
                log_channel: discord.TextChannel = self.bot.get_channel(channel)
                self.logs[guild] = log_channel
                return self.logs[guild]

            return None

        else:
            return self.logs[guild]

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        """
        An event called when a message is deleted.
        """
        if not message.author.bot:
            channel = await self.log_channel(message.guild.id)
            if channel:
                webhook = await self.prepare_webhook(channel)

                embed: discord.Embed = self.bot.embed(
                    description=f"**{message.author.mention} deleted a message in {message.channel.mention}:\
                    \n\n{message.content}**",
                    color=0xE74C3C,
                )
                embed.set_author(
                    name=f"{message.author}", icon_url=message.author.avatar.url
                )

                if self.embeds.get(message.guild.id, None):
                    embeds: List[discord.Embed] = self.embeds[message.guild.id][
                        "embeds"
                    ].append(embed)

                    self.embeds[message.guild.id].update(embed=embeds)
                    return

                self.embeds[message.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(
        self, payload: discord.RawBulkMessageDeleteEvent
    ) -> None:
        """
        An event called when a bulk amount of messages are deleted.
        """
        if len(payload.cached_messages) >= 10:
            channel = await self.log_channel(payload.guild_id)
            if channel:
                webhook = await self.prepare_webhook(channel)

                guild: discord.Guild = self.bot.get_guild(payload.guild_id)

                embed: discord.Embed = self.bot.embed(
                    description=f"**{len(payload.cached_messages)} message(s) bulk deleted\
                    in {guild.get_channel(payload.channel_id).mention}.**",
                    color=0xE74C3C,
                )
                embed.set_author(name=str(guild), icon_url=guild.icon.url)

                if self.embeds.get(payload.guild_id, None):
                    embeds: List[discord.Embed] = self.embeds[payload.guild_id][
                        "embeds"
                    ].append(embed)

                    self.embeds[payload.guild_id].update(embed=embeds)
                    return

                self.embeds[payload.guild_id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        """
        An event called when a message has been edited.
        """
        if not before.author.bot:
            channel = await self.log_channel(before.guild.id)
            if channel:
                webhook = await self.prepare_webhook(channel)

                splice = 2000
                name = str(before.author)
                avatar = before.author.avatar.url

                embeds = []

                if before.content == after.content:
                    if (
                        not before.pinned
                        and after.pinned
                        or before.pinned
                        and not after.pinned
                    ):
                        return

                elif len(before.content + after.content) >= 4000:
                    large_edits = []
                    total = len(before.content) / splice
                    for index, slice in enumerate(
                        range(0, len(before.content), splice), start=1
                    ):
                        embed: discord.Embed = self.bot.embed(
                            description=f"**{before.author.mention} edited a message in {before.channel.mention}:\
                            \n\nOriginal ({index}/{int(total)}):\n{before.content[slice:slice + splice]}**",
                            color=0xE67E22,
                        )
                        embed.set_author(name=name, icon_url=avatar)

                        large_edits.append(embed)

                    total = len(after.content) / splice
                    for index, slice in enumerate(
                        range(0, len(after.content), splice), start=1
                    ):
                        embed: discord.Embed = self.bot.embed(
                            description=f"**{after.author.mention} edited a message in {after.channel.mention}:\
                            \n\nEdited ({index}/{int(total)}):\n{after.content[slice:slice + splice]}**",
                            color=0xE67E22,
                        )
                        embed.set_author(name=name, icon_url=avatar)

                        large_edits.append(embed)

                    embeds.extend(large_edits)

                elif len(before.content + after.content) <= 4000:
                    embed: discord.Embed = self.bot.embed(
                        description=f"**{before.author.mention} edited a message in {before.channel.mention}:\
                        \n\nOriginal:\n{before.content}\n\nEdited:\n{after.content}**",
                        color=0xE67E22,
                    )
                    embed.set_author(name=name, icon_url=avatar)

                    embeds.append(embed)

                if self.embeds.get(before.guild.id, None):
                    embed: discord.Embed = self.embeds[before.guild.id]["embeds"]
                    embed.extend(embeds)

                    self.embeds[before.guild.id].update(embed=embed)
                    return

                self.embeds[before.guild.id] = {"webhook": webhook, "embeds": embeds}

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        """
        An event called when a channel has been created.
        """
        log_channel = await self.log_channel(channel.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            embed: discord.Embed = self.bot.embed(
                description=f"**{str(channel.type).title()} channel `{channel.name}` has been created.**",
                color=0x2ECC71,
            )
            embed.set_author(name=f"{channel.guild}", icon_url=channel.guild.icon.url)

            if self.embeds.get(channel.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[channel.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[channel.guild.id].update(embed=embeds)
                return

            self.embeds[channel.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel) -> None:
        """
        An event called when a channel has been deleted.
        """
        log_channel = await self.log_channel(channel.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            embed: discord.Embed = self.bot.embed(
                description=f"**{str(channel.type).title()} channel `{channel.name}` has been deleted.**",
                color=0xE74C3C,
            )
            embed.set_author(name=f"{channel.guild}", icon_url=channel.guild.icon.url)

            if self.embeds.get(channel.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[channel.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[channel.guild.id].update(embed=embeds)
                return

            self.embeds[channel.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ) -> None:
        """
        An event called whenever a channel is updated.
        """
        channel = await self.log_channel(before.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            changes = None

            before_overwrites: dict[int, discord.PermissionOverwrite] = {
                role.id: dict(overwrite)
                for role, overwrite in before.overwrites.items()
            }
            after_overwrites: dict[int, discord.PermissionOverwrite] = {
                role.id: dict(overwrite) for role, overwrite in after.overwrites.items()
            }

            role = []
            enabled = []
            defaulted = []
            disabled = []

            for before_role, after_role in zip(
                iter(before_overwrites), iter(after_overwrites)
            ):
                if before_role not in after_overwrites.keys():
                    changes = f"Permissions: Special permissions removed for <@&{before_role}>"
                    break

                elif before_role in after_overwrites.keys():
                    for before_overwrite, after_overwrite in zip(
                        before_overwrites[before_role].items(),
                        after_overwrites[after_role].items(),
                    ):
                        before_keys, before_value = before_overwrite
                        after_keys, after_value = after_overwrite

                        if before_value != after_value:
                            permission = {
                                True: "Enabled",
                                False: "Disabled",
                                None: "Defaulted",
                            }

                            after_key = (
                                after_keys.replace("_", " ")
                                .replace("guild", "server")
                                .title()
                            )

                            if not role.count(f"<@&{before_role}>"):
                                if before_role == after.guild.default_role.id:
                                    if not role.count("@everyone"):
                                        role.append("@everyone")

                                else:
                                    role.append(f"<@&{before_role}>")

                            if permission[after_value] == "Enabled":
                                enabled.append(after_key)

                            elif permission[after_value] == "Disabled":
                                disabled.append(after_key)

                            elif permission[after_value] == "Defaulted":
                                defaulted.append(after_key)

            if enabled or defaulted or disabled:
                enables = "Enabled: " + ", ".join(enabled) + "\n"
                disables = "Disabled: " + ", ".join(disabled) + "\n"
                defaults = "Defaulted: " + ", ".join(defaulted) + "\n"

                results = f"{enables if enabled else ''}\
                            {disables if disabled else ''}\
                            {defaults if defaulted else ''}"

                changes = (
                    f"Permission(s) updated for ({len(role)}) role(s):\n\n{results}"
                )

            elif before.name != after.name:
                changes = f"Name: {before.name} -> {after.name}"

            elif before.category != after.category:
                changes = (
                    f"Category: {before.category or 'N/A'} -> {after.category or 'N/A'}"
                )

            embed: discord.Embed = self.bot.embed(
                description=f"**{str(after.type).title()} channel\
                `{after.name}` has been updated.\n\n{changes}**",
                color=0xE67E22,
            )
            embed.set_author(name=str(before.guild), icon_url=before.guild.icon.url)

            if role:
                joined_roles = ", ".join(role)
                embed.add_field(
                    name=f"({len(role)}) role(s) updated", value=joined_roles
                )

            if changes:
                if self.embeds.get(before.guild.id, None):
                    embeds: List[discord.Embed] = self.embeds[before.guild.id][
                        "embeds"
                    ].append(embed)

                    self.embeds[before.guild.id].update(embed=embeds)
                    return

                self.embeds[before.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(
        self,
        channel: Union[discord.abc.GuildChannel, discord.Thread],
        last_pin: Optional[datetime.datetime],
    ) -> None:
        """
        An event called when a message was pinned/unpinned.
        """
        log_channel = await self.log_channel(channel.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            embed: discord.Embed = self.bot.embed(
                description=f"**Pinned message(s) in the {str(channel.type).title()} channel\
                `{channel.name}` has been updated.**",
                color=0xE67E22,
            )
            embed.set_author(name=f"{channel.guild}", icon_url=channel.guild.icon.url)

            if self.embeds.get(channel.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[channel.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[channel.guild.id].update(embed=embeds)
                return

            self.embeds[channel.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_thread_join(self, thread: discord.Thread) -> None:
        """
        An event called when a thread was created/joined.
        """
        log_channel = await self.log_channel(thread.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            changes = None

            if not thread.me:
                changes = "created."

            elif thread.me:
                changes = "joined."

            embed: discord.Embed = self.bot.embed(
                description=f"**{thread.mention} has been {changes}**", color=0x2ECC71
            )
            embed.set_author(name=f"{thread.guild}", icon_url=thread.guild.icon.url)

            if changes:
                if self.embeds.get(thread.guild.id, None):
                    embeds: List[discord.Embed] = self.embeds[thread.guild.id][
                        "embeds"
                    ].append(embed)

                    self.embeds[thread.guild.id].update(embed=embeds)
                    return

                self.embeds[thread.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        """
        An event called when a thread was deleted.
        """
        log_channel = await self.log_channel(thread.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            embed: discord.Embed = self.bot.embed(
                description=f"**{thread.name} was deleted.**", color=0x2ECC71
            )
            embed.set_author(name=f"{thread.guild}", icon_url=thread.guild.icon.url)

            if self.embeds.get(thread.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[thread.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[thread.guild.id].update(embed=embeds)
                return

            self.embeds[thread.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_thread_update(
        self, before: discord.Thread, after: discord.Thread
    ) -> None:
        """
        An event called when a thread has been updated.
        """
        log_channel = await self.log_channel(after.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            changes = None

            if before.archived != after.archived:
                changes = f"Archived: {before.archived} -> {after.archived}"

            elif before.category != after.category:
                changes = f"Category: {before.category} -> {after.category}"

            elif before.locked != after.locked:
                changes = f"Locked: {before.locked} -> {after.locked}"

            embed: discord.Embed = self.bot.embed(
                description=f"**{after.mention} has been updated.\n\n{changes}**",
                color=0x2ECC71,
            )
            embed.set_author(name=f"{after.guild}", icon_url=after.guild.icon.url)

            if changes:
                if self.embeds.get(after.guild.id, None):
                    embeds: List[discord.Embed] = self.embeds[after.guild.id][
                        "embeds"
                    ].append(embed)

                    self.embeds[after.guild.id].update(embed=embeds)
                    return

                self.embeds[after.guild.id] = {"webhook": webhook, "embeds": [embed]}

    # Deprecated due to changes in Discord API
    async def on_member_parsing(
        self, channel: discord.abc.GuildChannel, member: discord.Member, message: str
    ) -> str:
        """
        |coro|

        Returns a formatted string for custom messages in `on_member_x` events.
        """
        return message.format(
            user=member.mention,
            user_id=member.id,
            user_name=member.name,
            user_discriminator=member.discriminator,
            user_avatar=member.avatar.url,
            server=member.guild.name,
            server_id=member.guild.id,
            server_icon=member.guild.icon.url,
            server_owner_id=member.guild.owner.id,
            server_owner=member.guild.owner.mention,
            server_region=member.guild.region,
            server_members=member.guild.member_count,
            channel=channel.mention,
            channel_name=channel.name,
            channel_id=channel.id,
            user_bot=member.bot,
            server_verification=member.guild.verification_level,
            server_joined_at=member.guild.me.joined_at.strftime("%b. %d, %Y"),
            channel_type=channel.type[0],
            user_position=sum(
                user.joined_at < member.joined_at
                for user in member.guild.members
                if member.joined_at is not None
            )
            + 1,
            server_created_at=member.guild.created_at.strftime("%b. %d"),
            user_created_at=member.created_at.strftime("%b. %d"),
        )

    # Deprecated due to changes in Discord API
    async def member_channel(
        self, event: str, guild: discord.Guild, member: discord.Member
    ):
        # Optional[tuple[discord.TextChannel, str]] apparently raises an error?
        # Will look into this soon
        """
        |coro|

        A method that attempts to locate a :class:`discord.TextChannel` for `join` and
        `remove` events. If found, channel and message parsing will be completed.
        """
        if event == "join":
            join: List = await self.bot.pool.fetch(
                "SELECT join, welcome FROM guilds WHERE guild = $1", guild.id
            )
            if join:
                data: List = join[0]
                channel: discord.TextChannel = guild.get_channel(data[7])
                if channel:
                    join_message = await self.on_member_parsing(
                        channel, member, data[9]
                    )
                    return channel, join_message

        elif event == "leave":
            leave: List = await self.bot.pool.fetch(
                "SELECT leave, goodbye FROM guilds WHERE guild = $1", guild.id
            )
            if leave:
                data: List = leave[0]
                channel: discord.TextChannel = guild.get_channel(data[8])
                if channel:
                    leave_message = await self.on_member_parsing(
                        channel, member, data[10]
                    )
                    return channel, leave_message

        else:
            return None

    # Deprecated due to changes in Discord API
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """
        An event called whenever a member joins a server.
        """
        log_channel = await self.log_channel(member.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            channel, text = await self.member_channel("join", member.guild, member)
            if channel:
                embed: discord.Embed = self.bot.embed(description=text, color=0x3498DB)
                embed.set_author(name=str(member), icon_url=member.avatar.url)
                embed.set_thumbnail(url=member.avatar.url)
                await channel.send(embed=embed)

            embed: discord.Embed = self.bot.embed(
                description=f"**{member} has joined {member.guild}**", color=0x2ECC71
            )
            embed.set_author(name=str(member), icon_url=member.avatar.url)

            if self.embeds.get(member.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[member.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[member.guild.id].update(embed=embeds)
                return

            self.embeds[member.guild.id] = {"webhook": webhook, "embeds": [embed]}

    # Deprecated due to changes in Discord API
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        log_channel = await self.log_channel(member.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            leave, text = await self.member_channel("leave", member.guild, member)
            if leave:
                embed: discord.Embed = self.bot.embed(description=text, color=0x3498DB)
                embed.set_author(name=str(member), icon_url=member.avatar.url)
                embed.set_thumbnail(url=member.avatar.url)
                await leave.send(embed=embed)

            embed: discord.Embed = self.bot.embed(
                description=f"**{member} has left {member.guild}**", color=0xE74C3C
            )
            embed.set_author(name=str(member), icon_url=member.avatar.url)

            if self.embeds.get(member.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[member.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[member.guild.id].update(embed=embeds)
                return

            self.embeds[member.guild.id] = {"webhook": webhook, "embeds": [embed]}

    # Deprecated due to changes in Discord API
    @commands.Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        """
        An event called when member data has been updated.
        """
        channel = await self.log_channel(before.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            changes = ""

            if before.nick != after.nick:
                changes += f"Nickname: {before.display_name} -> {after.display_name}\n"

            elif before.pending != after.pending:
                changes += f"Pending Verification: {before.pending} -> {after.pending}"

            elif len(before.roles) != len(after.roles):
                added = []
                removed = []
                total = "Roles:\n\n"

                for old in before.roles:
                    if not old in after.roles:
                        removed.append(old.mention or old.name)

                for new in after.roles:
                    if not new in before.roles:
                        added.append(new.mention or new.name)

                if len(added) >= 1:
                    total += f"Role(s) Added: {', '.join(added)}\n"

                if len(removed) >= 1:
                    total += f"Role(s) Removed: {', '.join(removed)}\n"

                if len(added) >= 1 or len(removed) >= 1:
                    changes += total

            if changes == "":
                return

            embed: discord.Embed = self.bot.embed(
                description=f"**{before.mention}'s profile updated:\n\n{changes}**",
                color=0xE67E22,
            )
            embed.set_author(name=f"{before}", icon_url=before.avatar.url)

            if self.embeds.get(before.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[before.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[before.guild.id].update(embed=embeds)
                return

            self.embeds[before.guild.id] = {"webhook": webhook, "embeds": [embed]}

    # Deprecated due to changes in Discord API
    @commands.Cog.listener()
    async def on_presence_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        """
        An event called when a member's activity/presence has been updated.
        """
        channel = await self.log_channel(before.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            changes = ""

            if before.status != after.status:
                changes += f"Status: {before.status} -> {after.status}\n".replace(
                    "dnd", "do not disturb"
                ).title()

            elif before.activity != after.activity:
                before_type = ""
                after_type = ""

                before_name = ""
                after_name = ""

                if before.activity:
                    before_type += (
                        before.activity.type[0].title()
                        or before.activity.type[0].title()
                    )

                if after.activity:
                    after_type += after.activity.type[0].title()

                try:
                    before_name += before.activity.name
                except AttributeError:
                    before_name += "N/A"

                try:
                    after_name += after.activity.name
                except AttributeError:
                    after_name += "N/A"

                if before_name != after_name:
                    if isinstance(before.activity, discord.BaseActivity) or isinstance(
                        after.activity, discord.BaseActivity
                    ):
                        changes += f"Activity: {before_type if before_type != 'Custom' else ''} {before_name} -> {after_type if after_type != 'Custom' else ''} {after_name}\n"

                    elif isinstance(before.activity, discord.Spotify) or isinstance(
                        after.activity, discord.Spotify
                    ):
                        before_title = ""
                        after_title = ""
                        if before.activity:
                            try:
                                before_title += f"{before.activity.title} by {before.activity.artist} on Spotify"
                            except AttributeError:
                                pass

                        if after.activity:
                            try:
                                after_title += f"{after.activity.title} by {after.activity.artist} on Spotify"
                            except AttributeError:
                                pass

                        changes += f"Activity: {before_type + ' to' if before_type != '' else ''} {before_title if before_title != '' else 'N/A'} -> {after_type + ' to' if after_type != '' else ''} {after_title if after_title != '' else 'N/A'}\n"

            if changes == "":
                return

            embed: discord.Embed = self.bot.embed(
                description=f"**{before.mention}'s presence updated:\n\n{changes}**",
                color=0xE67E22,
            )
            embed.set_author(name=f"{before}", icon_url=before.avatar.url)

            if self.embeds.get(before.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[before.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[before.guild.id].update(embed=embeds)
                return

            self.embeds[before.guild.id] = {"webhook": webhook, "embeds": [embed]}

    # Deprecated due to changes in Discord API
    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User) -> None:
        """
        An event called when user data has been updated.
        """
        if not before.bot:
            guilds: List[discord.Guild] = self.bot.guilds
            for guild in guilds:
                channel = await self.log_channel(guild.id)
                if channel:
                    webhook = await self.prepare_webhook(channel)
                    for member in guild.members:
                        if member.id == before.id:

                            changes = ""
                            avatar = ""

                            if before.avatar != after.avatar:
                                changes += f"Avatar: [Old]({before.avatar.url}) -> [New]({after.avatar.url})"
                                avatar += str(after.avatar.url)

                            elif (
                                before.name != after.name
                                or before.discriminator != after.discriminator
                            ):
                                changes += f"Username: {before} -> {after}"

                            if not changes:
                                return

                            embed: discord.Embed = self.bot.embed(
                                description=f"**{guild.get_member(before.id).mention} updated their account.\n\n{changes}**",
                                color=0xE67E22,
                            )
                            embed.set_thumbnail(url=avatar)

                            if self.embeds.get(guild.id, None):
                                embeds: List[discord.Embed] = self.embeds[guild.id][
                                    "embeds"
                                ].append(embed)

                                self.embeds[guild.id].update(embed=embeds)
                                return

                            self.embeds[guild.id] = {
                                "webhook": webhook,
                                "embeds": [embed],
                            }

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """
        An event called when the bot joins a server.
        """
        if not hasattr(self, "owners"):
            self.owners: discord.User = [
                await self.bot.fetch_user(owner) for owner in self.bot.owner_ids
            ]

        for owner in self.owners:
            time = discord.utils.format_dt(discord.utils.utcnow())
            await owner.send(
                f"{time}\n Guilds: {len(self.bot.guilds)}\n\n{guild.me} has joined {guild} with a member count of {guild.member_count}."
            )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """
        An event called when the bot leaves a server.
        """
        if not hasattr(self, "owners"):
            self.owners: discord.User = [
                await self.bot.fetch_user(owner) for owner in self.bot.owner_ids
            ]

        for owner in self.owners:
            time = discord.utils.format_dt(discord.utils.utcnow())
            await owner.send(
                f"{time}\n Guilds: {len(self.bot.guilds)}\n\n{guild.me} left or was removed from {guild}."
            )

    @commands.Cog.listener()
    async def on_guild_update(
        self, before: discord.Guild, after: discord.Guild
    ) -> None:
        """
        An event called when a server has been updated.
        """
        channel = await self.log_channel(before.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            changes = None

            if before.name != after.name:
                changes = f"Name: {before.name} -> {after.name}"

            elif before.icon != after.icon:
                changes = (
                    f"Server Icon: [Old]({before.icon.url}) -> [New]({after.icon.url})"
                )

            elif before.region != after.region:
                changes = f"Region: {before.region} -> {after.region}"

            elif before.owner != after.owner:
                changes = f"Owner: {before.owner} -> {after.owner}"

            elif before.verification_level != after.verification_level:
                changes = f"Verification: {before.verification_level} -> {after.verification_level}"

            embed: discord.Embed = self.bot.embed(
                description=f"**Changes were made to {after}\n\n{changes}**",
                color=0xE67E22,
            )
            embed.set_author(name=f"{after}", icon_url=after.icon.url)
            embed.set_thumbnail(url=after.banner.url)

            if changes:
                if self.embeds.get(before.id, None):
                    embeds: List[discord.Embed] = self.embeds[before.id][
                        "embeds"
                    ].append(embed)

                    self.embeds[before.id].update(embed=embeds)
                    return

                self.embeds[before.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        """
        An event called when a role has been created.
        """
        channel = await self.log_channel(role.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed: discord.Embed = self.bot.embed(
                description=f"**Role `{role.name}` has been created.**", color=0x2ECC71
            )
            embed.set_author(name=str(role.guild), icon_url=role.guild.icon.url)

            if self.embeds.get(role.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[role.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[role.guild.id].update(embed=embeds)
                return

            self.embeds[role.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        """
        An event called when a role has been deleted.
        """
        channel = await self.log_channel(role.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed: discord.Embed = self.bot.embed(
                description=f"**Role `{role.name}` has been deleted.**", color=0xE74C3C
            )
            embed.set_author(name=str(role.guild), icon_url=role.guild.icon.url)

            if self.embeds.get(role.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[role.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[role.guild.id].update(embed=embeds)
                return

            self.embeds[role.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_role_update(
        self, before: discord.Role, after: discord.Role
    ) -> None:
        """
        An event called when a role has been updated.
        """
        channel = await self.log_channel(before.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            changes = None

            if before.name != after.name:
                changes = f"Name: {before.name} -> {after.name}"

            elif before.colour != after.colour:
                changes = f"Color: {before.colour} -> {after.colour}"

            elif before.permissions.value != after.permissions.value:

                added = []
                removed = []
                total = "Permissions:\n\n"

                for key, _ in dict(
                    discord.Permissions(before.permissions.value)
                ).items():
                    if not key in [
                        k
                        for k, v in dict(
                            discord.Permissions(after.permissions.value)
                        ).items()
                        if not v
                    ]:
                        removed.append(
                            key.replace("_", " ").replace("guild", "server").title()
                        )

                for k, _ in dict(discord.Permissions(after.permissions.value)).items():
                    if not k in [
                        key
                        for key, value in dict(
                            discord.Permissions(before.permissions.value)
                        ).items()
                        if value
                    ]:
                        added.append(
                            k.replace("_", " ").replace("guild", "server").title()
                        )

                if len(added) >= 1:
                    total += f"✅ Allowed Permission(s):\n{', '.join(added)}\n\n"

                if len(removed) >= 1:
                    total += f"❌ Denied Permission(s):\n{', '.join(removed)}\n\n"

                if len(added) >= 1 or len(removed) >= 1:
                    changes = total

            embed: discord.Embed = self.bot.embed(
                description=f"**Changes were made to the role `{after.name}`\n\n{changes}**",
                color=0xE67E22,
            )
            embed.set_author(name=f"{after.guild}", icon_url=after.guild.icon.url)
            embed.set_thumbnail(url=after.guild.banner.url)

            if changes:
                if self.embeds.get(before.id, None):
                    embeds: List[discord.Embed] = self.embeds[before.id][
                        "embeds"
                    ].append(embed)

                    self.embeds[before.id].update(embed=embeds)
                    return

                self.embeds[before.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self, guild: discord.Guild, before: discord.Emoji, after: discord.Emoji
    ) -> None:
        """
        An event called whenever a guild emoji has been updated.
        """
        if len(before) != len(after):
            channel = await self.log_channel(guild.id)
            if channel:
                webhook = await self.prepare_webhook(channel)

                embed: discord.Embed = self.bot.embed(
                    description=f"**{guild} emoji(s) have been updated.**",
                    color=0xE67E22,
                )
                embed.set_author(name=str(guild), icon_url=guild.icon.url)

                if self.embeds.get(guild.id, None):
                    embeds: List[discord.Embed] = self.embeds[guild.id][
                        "embeds"
                    ].append(embed)

                    self.embeds[guild.id].update(embed=embeds)
                    return

                self.embeds[guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self,
        guild: discord.Guild,
        before: discord.GuildSticker,
        after: discord.GuildSticker,
    ) -> None:
        """
        An event called whenever a guild sticker has been updated.
        """
        if len(before) != len(after):
            channel = await self.log_channel(guild.id)
            if channel:
                webhook = await self.prepare_webhook(channel)

                embed: discord.Embed = self.bot.embed(
                    description=f"**{guild} sticker(s) have been updated.**",
                    color=0xE67E22,
                )
                embed.set_author(name=str(guild), icon_url=guild.icon.url)

                if self.embeds.get(guild.id, None):
                    embeds: List[discord.Embed] = self.embeds[guild.id][
                        "embeds"
                    ].append(embed)

                    self.embeds[guild.id].update(embed=embeds)
                    return

                self.embeds[guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """
        An event called whenever a member joins/leaves a voice channel.
        """
        channel = await self.log_channel(member.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            if before.channel != after.channel:
                before_type = (
                    f"connected to {after.channel.type} channel ".replace("_", " ")
                    if after.channel
                    else f"disconnected from {before.channel.type} channel ".replace(
                        "_", " "
                    )
                )

                after_type = (
                    f"`{after.channel}`" if after.channel else f"`{before.channel}`"
                )
                color = 0xE74C3C if before_type.startswith("disconnected") else 0x2ECC71
                embed: discord.Embed = self.bot.embed(
                    description=f"**{member.mention} {before_type} {after_type}**",
                    color=color,
                )

                if self.embeds.get(member.guild.id, None):
                    embeds: List[discord.Embed] = self.embeds[member.guild.id][
                        "embeds"
                    ].append(embed)

                    self.embeds[member.guild.id].update(embed=embeds)
                    return

                self.embeds[member.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_stage_instance_create(self, stage: discord.StageInstance) -> None:
        """
        An event called whenever a stage channel is created.
        """
        channel = await self.log_channel(stage.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed: discord.Embed = self.bot.embed(
                description=f"**`{stage.channel.name}` has been created.**",
                color=0x2ECC71,
            )

            if self.embeds.get(stage.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[stage.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[stage.guild.id].update(embed=embeds)
                return

            self.embeds[stage.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_stage_instance_delete(self, stage: discord.StageInstance) -> None:
        """
        An event called whenever a stage channel is deleted.
        """
        channel = await self.log_channel(stage.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed: discord.Embed = self.bot.embed(
                description=f"**`{stage.channel.name}` has been deleted.**",
                color=0x2ECC71,
            )

            if self.embeds.get(stage.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[stage.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[stage.guild.id].update(embed=embeds)
                return

            self.embeds[stage.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_stage_instance_create(
        self, before: discord.StageInstance, after: discord.StageInstance
    ) -> None:
        """
        An event called whenever a stage channel is updated.
        """
        channel = await self.log_channel(before.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            changes = None

            if before.channel.name != after.channel.name:
                changes = f"Name: {before.channel.name} -> {after.channel.name}"

            elif before.channel.category != after.channel.category:
                changes = f"Category: {before.channel.category.name} -> {after.channel.category.name}"

            elif before.topic != after.topic:
                changes = f"Topic: {before.topic} -> {after.topic}"

            elif before.privacy_level != after.privacy_level:
                before_privacy = (
                    before.privacy_level.__str__()
                    .replace("guild", "server")
                    .replace("_", " ")
                    .title()
                )
                after_privacy = (
                    after.privacy_level.__str__()
                    .replace("guild", "server")
                    .replace("_", " ")
                    .title()
                )
                changes = f"Privacy Level: {before_privacy} -> {after_privacy}"

            elif before.discoverable_disabled != after.discoverable_disabled:
                before_discover = True if not before.discoverable_disabled else False
                after_discover = True if not after.discoverable_disabled else False
                changes = f"Discoverable: {before_discover} -> {after_discover}"

            embed: discord.Embed = self.bot.embed(
                description=f"**`{before.channel.name}` has been updated:\n\n{changes}**",
                color=0x2ECC71,
            )

            if self.embeds.get(before.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[before.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[before.guild.id].update(embed=embeds)
                return

            self.embeds[before.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_member_ban(
        self, guild: discord.Guild, user: Union[discord.User, discord.Member]
    ) -> None:
        """
        An event called whenever a member has been banned from a guild.
        """
        channel = await self.log_channel(guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed: discord.Embed = self.bot.embed(
                description=f"**{user} has been banned.**", color=0xE74C3C
            )

            if self.embeds.get(guild.id, None):
                embeds: List[discord.Embed] = self.embeds[guild.id]["embeds"].append(
                    embed
                )

                self.embeds[guild.id].update(embed=embeds)
                return

            self.embeds[guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User) -> None:
        """
        An event called whenever a user has been unbanned from a guild.
        """
        channel = await self.log_channel(guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed: discord.Embed = self.bot.embed(
                description=f"**{user} has been unbanned.**", color=0x2ECC71
            )

            if self.embeds.get(guild.id, None):
                embeds: List[discord.Embed] = self.embeds[guild.id]["embeds"].append(
                    embed
                )

                self.embeds[guild.id].update(embed=embeds)
                return

            self.embeds[guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite) -> None:
        """
        An event called whenever a channel invite has been created.
        """
        channel = await self.log_channel(invite.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            expire = []
            expires = ""

            if invite.max_age:
                max_age = discord.utils.format_dt(
                    discord.utils.utcnow() + datetime.timedelta(seconds=invite.max_age),
                    "R",
                )
                expire.append(f"in {max_age}")

            if invite.max_uses:
                expire.append(f"in {invite.max_uses} uses")

            if len(expire) == 0:
                expires += ", invite will not expire"

            elif len(expire) == 1:
                expires += f", invite will expire {expire[0]}"

            elif len(expire) == 2:
                expires += f", invite will expire {expire[0]} and {expire[1]}"

            embed: discord.Embed = self.bot.embed(
                description=f"**An [invite]({invite.url}) link has been created by `{invite.inviter}` in channel `{invite.channel}`{expires}.**",
                color=0x2ECC71,
            )

            if self.embeds.get(invite.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[invite.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[invite.guild.id].update(embed=embeds)
                return

            self.embeds[invite.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite) -> None:
        """
        An event called whenever a channel invite has been deleted.
        """
        channel = await self.log_channel(invite.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed: discord.Embed = self.bot.embed(
                description=f"**An invite link created by `{invite.inviter}` from channel `{invite.channel}` has been deleted.**",
                color=0xE74C3C,
            )

            if self.embeds.get(invite.guild.id, None):
                embeds: List[discord.Embed] = self.embeds[invite.guild.id][
                    "embeds"
                ].append(embed)

                self.embeds[invite.guild.id].update(embed=embeds)
                return

            self.embeds[invite.guild.id] = {"webhook": webhook, "embeds": [embed]}


def setup(bot):
    bot.add_cog(Events(bot))
