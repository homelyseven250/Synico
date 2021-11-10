import requests
import io
import textwrap
import math
import discord
from discord.ext import commands
from PIL import Image, ImageFont, ImageDraw, ImageFilter
from main import Bot


class Levels(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.author.bot:
            user = await self.bot.pool.fetchrow(
                "SELECT * FROM public.levels WHERE guild=$1 AND user_id=$2",
                message.guild.id,
                message.author.id,
            )
            if user == None:
                await self.bot.pool.execute(
                    "INSERT INTO public.levels (guild, user_id, level, messages) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
                    message.guild.id,
                    message.author.id,
                    1,
                    1,
                )
            else:
                if user[3] == math.pow(user[2], 2):
                    await self.bot.pool.execute(
                        "INSERT INTO public.levels (guild, user_id, level, messages) VALUES ($1, $2, $3, $4) ON CONFLICT (guild, user_id) DO UPDATE SET level=$3, messages=$4",
                        message.guild.id,
                        message.author.id,
                        user[2] + 1,
                        user[3] + 1,
                    )
                    await message.reply(f'GG {message.author.mention}, you just advanced to level {user[2]}')
                else:
                    await self.bot.pool.execute(
                        "INSERT INTO public.levels (guild, user_id, level, messages) VALUES ($1, $2, $3, $4) ON CONFLICT (guild, user_id) DO UPDATE SET messages=$4",
                        message.guild.id,
                        message.author.id,
                        user[2],
                        user[3] + 1,
                    )

    @commands.Command
    async def level(self, context: commands.Context):
        user = await self.bot.pool.fetchrow(
            "SELECT * FROM public.levels WHERE guild=$1 AND user_id=$2",
            context.guild.id,
            context.author.id,
        )
        image = Image.open("gradientBig.jpg")
        image = image.resize((1920, 1080))
        image = image.filter(ImageFilter.GaussianBlur(radius=10))
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("Ubuntu-Medium.ttf", 92)
        margin = offset = image.width / 4
        for line in textwrap.wrap(context.author.display_name, width=40):
            draw.text((margin, offset), line, font=font, fill=(255, 255, 255))
            offset += font.getsize(line)[1]

        draw.text(
            ((image.width / 4) * 3, offset),
            f"Level {user[2]}",
            font=font,
            fill=(255, 255, 255),
            align="right",
        )
        draw.text(
            ((image.height / 10) * 1, (image.width / 10) * 1),
            context.guild.name,
            font=font,
            fill=(255, 255, 255),
            align="left",
        )
        # draw.rounded_rectangle(
        #     (
        #         (image.width / 5, image.height / 5 * 4),
        #         (image.width / 5 * 4, (image.height / 5 * 4) - 100),
        #     ),
        #     fill=(255, 255, 255),
        #     radius=100,
        # )
        draw.rounded_rectangle(
            (
                (image.width / 5, image.height / 5 * 4),
                (
                    (image.width / 5 * 4 / ((math.pow(user[2], 2) / user[3]))),
                    image.height / 5 * 4 - 100,
                ),
            ),
            fill=(0, 0, 0),
            width=5,
            radius=1,
            outline="black"
        )

        imageOut = io.BytesIO()
        image.save(
            imageOut,
            "png",
        )
        imageOut.seek(0)
        await context.reply(file=discord.File(fp=imageOut, filename="card.png"))


def setup(bot: Bot):
    bot.add_cog(Levels(bot))
