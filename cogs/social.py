import os
import random
import typing

import discord
from discord.ext import commands
from main import Bot


class Social(commands.Cog):
    """A module with various reactions."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.emotions = [
            "hungry",
            "bored",
            "excited",
            "angry",
            "sad",
            "scared",
            "surprised",
            "frustrated",
            "annoyed",
        ]
        self.actions = {
            "bite": ["bite", "chew on", "chomp", "take a bite out of", "nibble on"],
            "hug": [
                "hug",
                "share some love with",
                "comfort",
                "hug it out",
                "give a big hug to",
            ],
            "kiss": ["kiss", "smooch", "mwah", "give a peck"],
            "kill": [
                "exterminate",
                "kill",
                "destroy",
                "get rid of",
                "eliminate",
                "step in and kill",
            ],
            "slap": ["slap", "smack", "back-hand", "give a high-five to the face of"],
            "tired": ["sleepy", "tired", "exhausted", "pooped out"],
            "yay": ["excited", "joyful", "thrilled"],
        }

    def __emotion__(self) -> str:
        return random.choice(self.emotions)

    def __action__(self, cmd: str) -> str:
        return random.choice(self.actions[cmd])

    @staticmethod
    async def __embed__(
        context: commands.Context,
        cmd: str,
        image: typing.Union[str, discord.File],
        title: str = None,
    ) -> None:
        if isinstance(image, str):
            embed: discord.Embed = context.bot.embed(color=0x2ECC71)
            if title:
                embed.title = title
            embed.set_image(url=image)
            await context.send(embed=embed)

        elif isinstance(image, discord.File):
            embed: discord.Embed = context.bot.embed(color=0x2ECC71)
            if title:
                embed.title = title
            embed.set_image(url=f"attachment://{cmd}.gif")
            await context.send(file=image, embed=embed)

    def __react__(self, cmd: str):
        gif = random.choice(os.listdir(f"./gifs/{cmd}")[1:])
        with open(f"./gifs/{cmd}/" + gif, "rb") as fp:
            return discord.File(fp=fp, filename=f"{cmd}.gif")

    @commands.group(name="rp")
    async def _rp(self, context: commands.Context) -> None:
        pass

    @_rp.command()
    async def bite(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(description="Server member to bite."),
    ) -> None:
        """Take a bite out of someone."""
        await self.__embed__(
            context,
            context.command,
            self.__react__(context.command.name),
            f"{context.author} got {self.__emotion__()} and decided to {self.__action__(context.command.name)} {member}",
        )

    @_rp.command()
    async def blush(self, context: commands.Context) -> None:
        """React with a blushing gif."""
        await self.__embed__(
            context,
            context.command,
            self.__react__(context.command.name),
            f"{context.author} {context.command.name}ed",
        )

    @_rp.command()
    async def hug(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(
            description="Server member to give a hug to."
        ),
    ) -> None:
        """ "Give a user a warm hug."""
        await self.__embed__(
            context,
            context.command,
            self.__react__(context.command.name),
            f"{context.author} got {self.__emotion__()} and decided to {self.__action__(context.command.name)} {member}",
        )

    @_rp.command()
    async def kill(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(
            description="Server member to put an end to."
        ),
    ) -> None:
        """Put an end to a user."""
        if member.id == context.author.id:
            return await context.send("No can do buddy.")

        await self.__embed__(
            context,
            context.command,
            self.__react__(context.command.name),
            f"{context.author} got {self.__emotion__()} and decided to {self.__action__(context.command.name)} {member}",
        )

    @_rp.command()
    async def kiss(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(description="Server member to kiss."),
    ) -> None:
        """Give a smooch to that special someone."""
        await self.__embed__(
            context,
            context.command,
            self.__react__(context.command.name),
            f"{context.author} got {self.__emotion__()} and decided to {self.__action__(context.command.name)} {member}",
        )

    @_rp.command()
    async def laugh(self, context: commands.Context) -> None:
        """React with a laughing gif."""
        await self.__embed__(
            context,
            context.command,
            self.__react__(context.command.name),
            f"{context.author} {context.command.name}ed",
        )

    @_rp.command()
    async def mad(self, context: commands.Context) -> None:
        """React with an angry/mad gif possessed by your anger."""
        await self.__embed__(
            context,
            context.command,
            self.__react__(context.command.name),
            f"{context.author} is {context.command.name}",
        )

    @_rp.command()
    async def sad(self, context: commands.Context) -> None:
        """React with a gif full of your sadness."""
        await self.__embed__(
            context,
            context.command,
            self.__react__(context.command.name),
            f"{context.author} is {context.command.name}",
        )

    @_rp.command()
    async def slap(
        self,
        context: commands.Context,
        member: discord.Member = commands.Option(description="Server member to slap."),
    ) -> None:
        """Slap a user into the next life."""
        await self.__embed__(
            context,
            context.command,
            self.__react__(context.command.name),
            f"{context.author} got {self.__emotion__()} and decided to {self.__action__(context.command.name)} {member}",
        )

    @_rp.command()
    async def tired(self, context: commands.Context) -> None:
        """React with a sleep-deprived, tired gif."""
        await self.__embed__(
            context,
            context.command,
            self.__react__(context.command.name),
            f"{context.author} is feeling {self.__action__(context.command.name)}",
        )

    @_rp.command()
    async def yay(self, context: commands.Context) -> None:
        """React with a gif full of joy."""
        await self.__embed__(
            context,
            context.command,
            self.__react__(context.command.name),
            f"{context.author} is feeling {self.__action__(context.command.name)}",
        )


def setup(bot: Bot):
    bot.add_cog(Social(bot))
