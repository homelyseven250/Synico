import asyncio
import datetime
from typing import Optional, Union

import discord
from discord.ext import commands, tasks


class Events(commands.Cog):
    """
    A class that inherits from
    :class:`commands.Cog` with the
    intent to handle events and designate
    the output.
    """

    def __init__(self, bot):
        self.bot = bot
        self.embeds = {}
        self.logs = {}
        self.webhooks = {}

        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        """
        |coro|

        An asynchronous version of :method:`__init__`
        to access coroutines.
        """
        await self.dispatch_events.start()

    def cog_unload(self):
        """
        A method of :class:`commands.Cog` that
        is called upon the extension being
        removed interally. This allows for any
        needed cleanup.
        """
        self.dispatch_events.stop()
        return super().cog_unload()

    @tasks.loop(seconds=10, reconnect=True)
    async def dispatch_events(self):
        """
        A background task that is scheduled
        to run at an interval of 1 minute to output
        stored list containing :class:`discord.Embed`.
        """
        if len(self.embeds) >= 1:
            for guild in iter(self.embeds):
                if len(self.embeds[guild]["embeds"]) > 0:
                    webhook = self.embeds[guild]["webhook"]
                    embeds = self.embeds[guild]["embeds"][:10]
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

        A method that checks the local cache for a :class:`discord.Webhook`
        object that is designated for a :class:`discord.Guild`. If not found,
        this will attempt to use a pre-existing one or create one as a
        last resort.
        """
        if not self.webhooks.get(channel.guild.id, None):
            webhooks = await channel.webhooks()
            if webhooks:
                for webhook in webhooks:
                    if webhook.token:
                        return webhook

                webhook = await channel.create_webhook(name="Synico")
                self.webhooks[channel.guild.id] = webhook.url
                return webhook

        return discord.Webhook.from_url(
            self.webhooks[channel.guild.id], session=self.bot.cs
        )

    async def log_channel(self, guild: int) -> Optional[discord.TextChannel]:
        """
        |coro|

        A method that checks the local cache for a :class:`discord.TextChannel`
        id that is designated for a :class:`discord.Guild`.
        Returns a :class:`NoneType` if not found.
        """
        if not self.logs.get(guild, None):
            channel = await self.bot.pool.fetchval(
                "SELECT logs FROM guild WHERE guild_id = $1", guild
            )
            if channel:
                self.logs[guild] = self.bot.get_channel(channel)
                return self.logs[guild]

            return None

        return self.logs[guild]

    @commands.Cog.listener()
    async def on_command_completion(self, context: commands.Context):
        """
        An event called when a command is invoked successfully.
        """
        if context.command.cog:
            if context.command.cog.qualified_name == "moderation":
                channel = await self.log_channel(context.guild.id)
                if channel:
                    webhook = await self.prepare_webhook(channel)

                    embed = self.bot.embed(
                        description=f"**{context.author.mention} used [command]({context.message.jump_url})\
                        `{context.prefix}{context.command.name}` in {context.channel.mention}:\
                        \n\n{context.message.content}**",
                        color=0xE67E22,
                    )
                    embed.set_author(
                        name=f"{context.author}", icon_url=context.author.avatar.url
                    )

                    if self.embeds.get(context.guild.id, None):
                        embeds = self.embeds[context.guild.id]["embeds"].append(embed)

                        self.embeds[context.guild.id].update(embed=embeds)
                        return

                    self.embeds[context.guild.id] = {
                        "webhook": webhook,
                        "embeds": [embed],
                    }

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """
        An event called when a message is deleted.
        """
        if not message.author.bot:
            channel = await self.log_channel(message.guild.id)
            if channel:
                webhook = await self.prepare_webhook(channel)

                embed = self.bot.embed(
                    description=f"**{message.author.mention} deleted a message in {message.channel.mention}:\
                    \n\n{message.content}**",
                    color=0xE74C3C,
                )
                embed.set_author(
                    name=f"{message.author}", icon_url=message.author.avatar.url
                )

                if self.embeds.get(message.guild.id, None):
                    embeds = self.embeds[message.guild.id]["embeds"].append(embed)

                    self.embeds[message.guild.id].update(embed=embeds)
                    return

                self.embeds[message.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(
        self, payload: discord.RawBulkMessageDeleteEvent
    ):
        """
        An event called when uncached messages are deleted.
        """
        if len(payload.cached_messages) >= 10:
            channel = await self.log_channel(payload.guild_id)
            if channel:
                webhook = await self.prepare_webhook(channel)

                guild = self.bot.get_guild(payload.guild_id)

                embed = self.bot.embed(
                    description=f"**{len(payload.cached_messages)} message(s) bulk deleted\
                    in {guild.get_channel(payload.channel_id).mention}.**",
                    color=0xE74C3C,
                )
                embed.set_author(name=str(guild), icon_url=guild.icon.url)

                if self.embeds.get(payload.guild_id, None):
                    embeds = self.embeds[payload.guild_id]["embeds"].append(embed)

                    self.embeds[payload.guild_id].update(embed=embeds)
                    return

                self.embeds[payload.guild_id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """
        An event called when a :class:`discord.Message` receives an edt.

        The following non-exhaustive cases trigger this event:
        ------------------------------------------------------
            - A message has been pinned or unpinned.

            - The message content has been changed.

            - The message has received an embed.

            - The message’s embeds were suppressed or unsuppressed.

            - A call message has received an update to its participants or ending time.
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
                    for index, _ in enumerate(
                        range(0, len(before.content), splice), start=1
                    ):
                        embed = self.bot.embed(
                            description=f"**{before.author.mention} edited a message in {before.channel.mention}:\
                            \n\nOriginal ({index}/{int(total)}):\n{before.content[_:_ + splice]}**",
                            color=0xE67E22,
                        )
                        embed.set_author(name=name, icon_url=avatar)

                        large_edits.append(embed)

                    total = len(after.content) / splice
                    for index, _ in enumerate(
                        range(0, len(after.content), splice), start=1
                    ):
                        embed = self.bot.embed(
                            description=f"**{after.author.mention} edited a message in {after.channel.mention}:\
                            \n\nEdited ({index}/{int(total)}):\n{after.content[_:_ + splice]}**",
                            color=0xE67E22,
                        )
                        embed.set_author(name=name, icon_url=avatar)

                        large_edits.append(embed)

                    embeds.extend(large_edits)

                elif len(before.content + after.content) <= 4000:
                    mbed = self.bot.embed(
                        description=f"**{before.author.mention} edited a message in {before.channel.mention}:\
                        \n\nOriginal:\n{before.content}\n\nEdited:\n{after.content}**",
                        color=0xE67E22,
                    )
                    mbed.set_author(name=name, icon_url=avatar)

                    embeds.append(mbed)

                if self.embeds.get(before.guild.id, None):
                    embed = self.embeds[before.guild.id]["embeds"]
                    embed.extend(embeds)

                    self.embeds[before.guild.id].update(embed=embed)
                    return

                self.embeds[before.guild.id] = {"webhook": webhook, "embeds": embeds}

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """
        An event called whenever a guild channel is created.
        """
        log_channel = await self.log_channel(channel.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            embed = self.bot.embed(
                description=f"**{str(channel.type).title()} channel `{channel.name}` has been created.**",
                color=0x2ECC71,
            )
            embed.set_author(name=f"{channel.guild}", icon_url=channel.guild.icon.url)

            if self.embeds.get(channel.guild.id, None):
                embeds = self.embeds[channel.guild.id]["embeds"].append(embed)

                self.embeds[channel.guild.id].update(embed=embeds)
                return

            self.embeds[channel.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """
        An event called whenever a guild channel is deleted.
        """
        log_channel = await self.log_channel(channel.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            embed = self.bot.embed(
                description=f"**{str(channel.type).title()} channel `{channel.name}` has been deleted.**",
                color=0xE74C3C,
            )
            embed.set_author(name=f"{channel.guild}", icon_url=channel.guild.icon.url)

            if self.embeds.get(channel.guild.id, None):
                embeds = self.embeds[channel.guild.id]["embeds"].append(embed)

                self.embeds[channel.guild.id].update(embed=embeds)
                return

            self.embeds[channel.guild.id] = {"webhook": webhook, "embeds": [embed]}

    # Permission and overwrite changes need to be implemented.
    @commands.Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        """
        An event called whenever a guild channel is updated.
        """
        channel = await self.log_channel(before.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            changes = None

            before_overwrites = {
                role.id: dict(overwrite)
                for role, overwrite in before.overwrites.items()
            }
            after_overwrites = {
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

            embed = self.bot.embed(
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
                    embeds = self.embeds[before.guild.id]["embeds"].append(embed)

                    self.embeds[before.guild.id].update(embed=embeds)
                    return

                self.embeds[before.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(
        self,
        channel: Union[discord.abc.GuildChannel, discord.Thread],
        last_pin: Optional[datetime.datetime],
    ):
        """
        An event called whenever a message is pinned/unpinned in a guild channel.
        """
        log_channel = await self.log_channel(channel.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            embed = self.bot.embed(
                description=f"**Pinned message(s) in the {str(channel.type).title()} channel\
                `{channel.name}` has been updated.**",
                color=0xE67E22,
            )
            embed.set_author(name=f"{channel.guild}", icon_url=channel.guild.icon.url)

            if self.embeds.get(channel.guild.id, None):
                embeds = self.embeds[channel.guild.id]["embeds"].append(embed)

                self.embeds[channel.guild.id].update(embed=embeds)
                return

            self.embeds[channel.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_thread_join(self, thread: discord.Thread):
        """
        An event called whenever a thread is created or joined.
        """
        log_channel = await self.log_channel(thread.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            changes = None

            if not thread.me:
                changes = "created."

            elif thread.me:
                changes = "joined."

            embed = self.bot.embed(
                description=f"**{thread.mention} has been {changes}**", color=0x2ECC71
            )
            embed.set_author(name=f"{thread.guild}", icon_url=thread.guild.icon.url)

            if changes:
                if self.embeds.get(thread.guild.id, None):
                    embeds = self.embeds[thread.guild.id]["embeds"].append(embed)

                    self.embeds[thread.guild.id].update(embed=embeds)
                    return

                self.embeds[thread.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        """
        An event called whenever a thread is deleted.
        """
        log_channel = await self.log_channel(thread.guild.id)
        if log_channel:
            webhook = await self.prepare_webhook(log_channel)

            embed = self.bot.embed(
                description=f"**{thread.name} was deleted.**", color=0x2ECC71
            )
            embed.set_author(name=f"{thread.guild}", icon_url=thread.guild.icon.url)

            if self.embeds.get(thread.guild.id, None):
                embeds = self.embeds[thread.guild.id]["embeds"].append(embed)

                self.embeds[thread.guild.id].update(embed=embeds)
                return

            self.embeds[thread.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        """
        An event called whenever a thread is updated.
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

            embed = self.bot.embed(
                description=f"**{after.mention} has been updated.\n\n{changes}**",
                color=0x2ECC71,
            )
            embed.set_author(name=f"{after.guild}", icon_url=after.guild.icon.url)

            if changes:
                if self.embeds.get(after.guild.id, None):
                    embeds = self.embeds[after.guild.id]["embeds"].append(embed)

                    self.embeds[after.guild.id].update(embed=embeds)
                    return

                self.embeds[after.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        An event called whenever the client joins a guild.
        """
        if not hasattr(self, "owner"):
            self.owner: discord.User = await self.bot.fetch_user(220418804176388097)

        if self.owner:
            time = discord.utils.format_dt(discord.utils.utcnow())
            await self.owner.send(
                f"{time}\n Guilds: {len(self.bot.guilds)}\n\n\
                {guild.me} has joined {guild} with a member count of {guild.member_count}."
            )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """
        An event called whenever the client leaves or is removed from a guild.
        """
        if not hasattr(self, "owner"):
            self.owner: discord.User = await self.bot.fetch_user(220418804176388097)

        if self.owner:
            time = discord.utils.format_dt(discord.utils.utcnow())
            await self.owner.send(
                f"{time}\n Guilds: {len(self.bot.guilds)}\n\n{guild.me} left or was removed from {guild}."
            )

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        """
        An event called whenever a guild has been updated.
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

            embed = self.bot.embed(
                description=f"**Changes were made to {after}\n\n{changes}**",
                color=0xE67E22,
            )
            embed.set_author(name=f"{after}", icon_url=after.icon.url)
            embed.set_thumbnail(url=after.banner.url)

            if changes:
                if self.embeds.get(before.id, None):
                    embeds = self.embeds[before.id]["embeds"].append(embed)

                    self.embeds[before.id].update(embed=embeds)
                    return

                self.embeds[before.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """
        An event called whenever a role has been created in a guild.
        """
        channel = await self.log_channel(role.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed = self.bot.embed(
                description=f"**Role `{role.name}` has been created.**", color=0x2ECC71
            )
            embed.set_author(name=str(role.guild), icon_url=role.guild.icon.url)

            if self.embeds.get(role.guild.id, None):
                embeds = self.embeds[role.guild.id]["embeds"].append(embed)

                self.embeds[role.guild.id].update(embed=embeds)
                return

            self.embeds[role.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """
        An event called whenever a role has been deleted in a guild.
        """
        channel = await self.log_channel(role.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed = self.bot.embed(
                description=f"**Role `{role.name}` has been deleted.**", color=0xE74C3C
            )
            embed.set_author(name=str(role.guild), icon_url=role.guild.icon.url)

            if self.embeds.get(role.guild.id, None):
                embeds = self.embeds[role.guild.id]["embeds"].append(embed)

                self.embeds[role.guild.id].update(embed=embeds)
                return

            self.embeds[role.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        """
        An event called whenever a guild role has been updated.
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

            embed = self.bot.embed(
                description=f"**Changes were made to the role `{after.name}`\n\n{changes}**",
                color=0xE67E22,
            )
            embed.set_author(name=f"{after.guild}", icon_url=after.guild.icon.url)
            embed.set_thumbnail(url=after.guild.banner.url)

            if changes:
                if self.embeds.get(before.id, None):
                    embeds = self.embeds[before.id]["embeds"].append(embed)

                    self.embeds[before.id].update(embed=embeds)
                    return

                self.embeds[before.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self, guild: discord.Guild, before: discord.Emoji, after: discord.Emoji
    ):
        """
        An event called whenever a guild emoji has been updated.
        """
        if len(before) != len(after):
            channel = await self.log_channel(guild.id)
            if channel:
                webhook = await self.prepare_webhook(channel)

                embed = self.bot.embed(
                    description=f"**{guild} emoji(s) have been updated.**",
                    color=0xE67E22,
                )
                embed.set_author(name=str(guild), icon_url=guild.icon.url)

                if self.embeds.get(guild.id, None):
                    embeds = self.embeds[guild.id]["embeds"].append(embed)

                    self.embeds[guild.id].update(embed=embeds)
                    return

                self.embeds[guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self,
        guild: discord.Guild,
        before: discord.GuildSticker,
        after: discord.GuildSticker,
    ):
        """
        An event called whenever a guild sticker has been updated.
        """
        if len(before) != len(after):
            channel = await self.log_channel(guild.id)
            if channel:
                webhook = await self.prepare_webhook(channel)

                embed = self.bot.embed(
                    description=f"**{guild} sticker(s) have been updated.**",
                    color=0xE67E22,
                )
                embed.set_author(name=str(guild), icon_url=guild.icon.url)

                if self.embeds.get(guild.id, None):
                    embeds = self.embeds[guild.id]["embeds"].append(embed)

                    self.embeds[guild.id].update(embed=embeds)
                    return

                self.embeds[guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
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
                embed = self.bot.embed(
                    description=f"**{member.mention} {before_type} {after_type}**",
                    color=color,
                )

                if self.embeds.get(member.guild.id, None):
                    embeds = self.embeds[member.guild.id]["embeds"].append(embed)

                    self.embeds[member.guild.id].update(embed=embeds)
                    return

                self.embeds[member.guild.id] = {"webhook": webhook, "embeds": [embed]}

    # IMPLEMENT STAGE EVENTS HERE
    @commands.Cog.listener()
    async def on_stage_instance_create(self, stage: discord.StageInstance):
        """
        An event called whenever a stage channel is created.
        """
        channel = await self.log_channel(stage.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed = self.bot.embed(
                description=f"**`{stage.channel.name}` has been created.**",
                color=0x2ECC71,
            )

            if self.embeds.get(stage.guild.id, None):
                embeds = self.embeds[stage.guild.id]["embeds"].append(embed)

                self.embeds[stage.guild.id].update(embed=embeds)
                return

            self.embeds[stage.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_stage_instance_delete(self, stage: discord.StageInstance):
        """
        An event called whenever a stage channel is deleted.
        """
        channel = await self.log_channel(stage.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed = self.bot.embed(
                description=f"**`{stage.channel.name}` has been deleted.**",
                color=0x2ECC71,
            )

            if self.embeds.get(stage.guild.id, None):
                embeds = self.embeds[stage.guild.id]["embeds"].append(embed)

                self.embeds[stage.guild.id].update(embed=embeds)
                return

            self.embeds[stage.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_stage_instance_create(
        self, before: discord.StageInstance, after: discord.StageInstance
    ):
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

            embed = self.bot.embed(
                description=f"**`{before.channel.name}` has been updated:\n\n{changes}**",
                color=0x2ECC71,
            )

            if self.embeds.get(before.guild.id, None):
                embeds = self.embeds[before.guild.id]["embeds"].append(embed)

                self.embeds[before.guild.id].update(embed=embeds)
                return

            self.embeds[before.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_member_ban(
        self, guild: discord.Guild, user: Union[discord.User, discord.Member]
    ):
        """
        An event called whenever a member has been banned from a guild.
        """
        channel = await self.log_channel(guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed = self.bot.embed(
                description=f"**{user} has been banned.**", color=0xE74C3C
            )

            if self.embeds.get(guild.id, None):
                embeds = self.embeds[guild.id]["embeds"].append(embed)

                self.embeds[guild.id].update(embed=embeds)
                return

            self.embeds[guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """
        An event called whenever a user has been unbanned from a guild.
        """
        channel = await self.log_channel(guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed = self.bot.embed(
                description=f"**{user} has been unbanned.**", color=0x2ECC71
            )

            if self.embeds.get(guild.id, None):
                embeds = self.embeds[guild.id]["embeds"].append(embed)

                self.embeds[guild.id].update(embed=embeds)
                return

            self.embeds[guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
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

            embed = self.bot.embed(
                description=f"**An [invite]({invite.url}) link has been created by `{invite.inviter}` in channel `{invite.channel}`{expires}.**",
                color=0x2ECC71,
            )

            if self.embeds.get(invite.guild.id, None):
                embeds = self.embeds[invite.guild.id]["embeds"].append(embed)

                self.embeds[invite.guild.id].update(embed=embeds)
                return

            self.embeds[invite.guild.id] = {"webhook": webhook, "embeds": [embed]}

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        """
        An event called whenever a channel invite has been deleted.
        """
        channel = await self.log_channel(invite.guild.id)
        if channel:
            webhook = await self.prepare_webhook(channel)

            embed = self.bot.embed(
                description=f"**An invite link created by `{invite.inviter}` from channel `{invite.channel}` has been deleted.**",
                color=0xE74C3C,
            )

            if self.embeds.get(invite.guild.id, None):
                embeds = self.embeds[invite.guild.id]["embeds"].append(embed)

                self.embeds[invite.guild.id].update(embed=embeds)
                return

            self.embeds[invite.guild.id] = {"webhook": webhook, "embeds": [embed]}


def setup(bot):
    bot.add_cog(Events(bot))
