import discord
from discord.ext import commands
from utils import Tags, UserConverter, start_menu, tag_perms


class Info(commands.Cog):
    """
    A module to provide information
    on users and servers with handy utilities.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="avatar", aliases=["avi", "av"])
    async def _avatar(self, context: commands.Context, *, member: UserConverter = None):
        """
        Display a user's avatar.
        """
        member = member or context.author
        embed = self.bot.embed(color=0x2ECC71)
        embed.set_image(url=member.display_avatar)
        embed.set_footer(text=f"{member}'s Avatar")
        await context.send(embed=embed)

    @commands.command(aliases=["ui", "userinfo"])
    async def whois(self, context: commands.Context, *, member: UserConverter = None):
        """
        Display information on a user.
        """
        member = member or context.author

        created = discord.utils.format_dt(member.created_at)
        created_since = discord.utils.format_dt(member.created_at, "R")

        joined = discord.utils.format_dt(member.joined_at)
        joined_since = discord.utils.format_dt(member.joined_at, "R")

        special_permissions = [
            "administrator",
            "ban_members",
            "kick_members",
            "manage_messages",
        ]
        permissions = ", ".join(
            [
                key.replace("_", " ").replace("guild", "server").title()
                for key, value in dict(
                    discord.Permissions(member.guild_permissions.value)
                ).items()
                if value and key in special_permissions
            ]
        )

        roles = ", ".join([role.mention for role in member.roles[1:43]])

        embed = self.bot.embed(
            color=0x2ECC71,
            description=f"**Account Details**:\nJoined {context.guild} on {joined}\n({joined_since})\n\n \
            Registered Account on {created}\n({created_since})\n\n \
            **Key Permission(s)**:\n{permissions or 'N/A'}\n\n",
        )

        embed.add_field(name="Role(s)", value=roles[:1008] or "@everyone")
        embed.set_author(name=member.__str__(), icon_url=member.avatar.url)
        embed.set_thumbnail(url=member.avatar.url)

        await context.send(embed=embed)

    @commands.command(name="server-info", aliases=["server", "si", "gi"])
    async def server_info(self, context: commands.Context):
        """
        Display information on the server.
        """
        guild = context.guild

        created = discord.utils.format_dt(guild.created_at)
        created_since = discord.utils.format_dt(guild.created_at, "R")

        animated = len([emoji for emoji in guild.emojis if emoji.animated])
        static = len([emoji for emoji in guild.emojis if not emoji.animated])
        emojis = f"{len(guild.emojis)}/{guild.emoji_limit}"
        features = ", ".join(guild.features).lower().title()

        upload_limit = f"{round(guild.filesize_limit / 1000000)} MB"
        members = guild.member_count

        mfa = {0: "Admins don't require 2FA.", 1: "Admins required 2FA."}
        mfa = mfa[guild.mfa_level]

        verify = {
            0: "No requirements.",
            1: "Verified email required.",
            2: "Verified email and account age greater than 5 minutes required.",
            3: "Verified email, account age greater than 5 minutes, and a member of the server for 10 minutes required.",
            4: "Verified email, account age greater than 5 minutes, a member of the server for 10 minutes, and a verified phone number required.",
        }
        verification = verify[guild.verification_level.value]

        region = guild.region.value.replace("-", " ").title()
        roles = len(guild.roles)

        text = len(guild.text_channels)
        voice = len(guild.voice_channels)
        channels = len(guild.channels)
        categories = len(guild.categories)

        embed = self.bot.embed(
            color=0x2ECC71,
            description=f"Server created on {created} ({created_since}) located in the **{region}**\n\n \
            **Total Members:** {members}\n\n \
            **Text Channels:** {text}\n**Voice Channels:** {voice}\n**Total Channels:** {channels}\n**Total Categories:** {categories}\n\n \
            **Animated Emojis:** {animated}\n**Static Emojis:** {static}\n**Total Emojis:** {emojis}\n\n \
            **Total Roles:** {roles}\n**Upload Limit:** {upload_limit}\n**Admin MFA:** {mfa}\n**Server Verification:** {verification}\n\n \
            **Server Features:** {features or 'N/A'}",
        )

        embed.set_author(name=guild.__str__(), icon_url=guild.icon.url)
        embed.set_thumbnail(url=guild.icon.url)

        await context.send(embed=embed)

    @commands.command()
    async def tags(self, context: commands.Context):
        """
        Show server-made tags.
        """
        tags = await context.bot.pool.fetch(
            "SELECT * FROM tagging WHERE guild_id = $1", context.guild.id
        )
        if tags:
            await start_menu(context, Tags(tags))

        else:
            await context.send(f"No tags in {context.guild}")

    @commands.group(invoke_without_command=True)
    async def tag(self, context: commands.Context, *, tag: str):
        """
        Display a tag.
        """
        _tag = await context.bot.pool.fetchval(
            "SELECT content FROM tagging WHERE guild_id = $1 AND named = $2",
            context.guild.id,
            tag,
        )

        if _tag:
            count = (
                await context.bot.pool.fetchval(
                    "SELECT uses FROM tagging WHERE guild_id = $1 AND named = $2",
                    context.guild.id,
                    tag,
                )
                or 0
            )
            await context.bot.pool.execute(
                "UPDATE tagging SET uses = $1 WHERE guild_id = $2 AND named = $3",
                count + 1,
                context.guild.id,
                tag,
            )

            await context.send(
                content=_tag,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=False, roles=False, replied_user=True
                ),
            )
            return

        await context.send("Could not find a tag with that name.")

    @tag.command(name="add")
    async def add_tag(self, context: commands.Context, tag: str, *, content: str):
        """
        Create a tag.
        """
        if len(tag) > 256:
            await context.send(f"Tag name exceeded character limit. ({len(tag)}/256)")

        elif len(content) > 1725:
            await context.send(
                f"Tag content exceeded character limit. ({len(tag)}/1725)"
            )

        else:
            _tag = await context.bot.pool.fetchval(
                "SELECT named FROM tagging WHERE guild_id = $1 AND named = $2",
                context.guild.id,
                tag,
            )
            if not _tag:
                await context.send("Tag successfully created.")
                await context.bot.pool.execute(
                    "INSERT INTO tagging VALUES ($1, $2, $3, $4, $5, $6)",
                    context.guild.id,
                    context.author.id,
                    discord.utils.utcnow(),
                    0,
                    content[:1725],
                    tag[:256],
                )

            else:
                await context.send("Tag already exists.")

    @tag.command(name="info")
    async def tag_info(self, context: commands.Context, *, tag: str):
        """
        Display info on a tag.
        """
        _tag = await self.bot.pool.fetch(
            "SELECT * FROM tagging WHERE guild_id = $1 AND named = $2",
            context.guild.id,
            tag,
        )
        if _tag:
            user = _tag[0][1]
            owner = self.bot.cache["member"].get(user) or await context.bot.fetch_user(
                user
            )

            name = _tag[0][5]
            uses = _tag[0][3]
            date = _tag[0][2]

            embed = self.bot.embed(title=name[:256], color=0x2ECC71)
            embed.set_author(name=str(owner), icon_url=owner.avatar.url)
            embed.set_footer(
                text=f"Uses: {uses} | Created on {discord.utils.format_dt(date)}"
            )
            await context.send(embed=embed)

        else:
            await context.reply("Could not find a tag with that name.")

    @tag.command(name="delete")
    async def delete_tag(self, context: commands.Context, *, tag: str):
        """
        Delete a server's tag.
        """
        _tag = await self.bot.pool.fetch(
            "SELECT * FROM tagging WHERE guild_id = $1 AND named = $2",
            context.guild.id,
            tag,
        )
        if _tag:

            permission_check = tag_perms(context, _tag[1])
            if permission_check:
                await self.bot.pool.execute(
                    "DELETE FROM tagging WHERE guild_id = $1 AND named = $2",
                    context.guild.id,
                    tag,
                )
                await context.send("Tag has been deleted.")
                return

            await context.send("You are not allowed to delete this tag.")

        else:
            await context.send("Could not find a tag with that name.")

    @tag.command(name="edit")
    async def edit_tag(self, context: commands.Context, tag: str, *, content: str):
        """
        Edit the contents of a tag.
        """
        if len(content) > 1725:
            await context.send(
                f"Tag content exceeded character limit. ({len(tag)}/1725)"
            )

        _tag = await self.bot.pool.fetch(
            "SELECT * FROM tagging WHERE guild_id = $1 AND named = $2",
            context.guild.id,
            tag,
        )
        if _tag:

            permission_check = tag_perms(context, _tag[1])
            if permission_check:
                await context.bot.pool.execute(
                    "UPDATE tagging SET contents = $1 WHERE guild_id = $2 AND named = $3",
                    content,
                    context.guild.id,
                    tag,
                )
                await context.send(content="Tag has been updated.")
                return

            await context.send("You are not allowed to edit this tag.")

        else:
            await context.send("Could not find a tag with that name.")


def setup(bot):
    bot.add_cog(Info(bot))
