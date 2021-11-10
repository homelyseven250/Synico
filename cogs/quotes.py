import requests
import io
import textwrap
import discord
from discord.ext import commands
from PIL import Image, ImageFont, ImageDraw, ImageFilter
from main import Bot

class Quotes(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    def get_dominant_color(self, pil_img):
        img = pil_img.copy()
        img.convert("RGB")
        img.resize((1, 1), resample=0)
        dominant_color = img.getpixel((0, 0))
        return dominant_color


    def hilo(self, a, b, c):
        if c < b: b, c = c, b
        if b < a: a, b = b, a
        if c < b: b, c = c, b
        return a + c

    def complement(self, r, g, b):
        k = self.hilo(r, g, b)
        return tuple(k - u for u in (r, g, b))

        
    
    @commands.Command
    async def quote(self, context: commands.Context):
        await context.defer()
        quote = requests.get('https://quotable.io/random')
        imageData = requests.get('https://api.unsplash.com/photos/random?query=nature&orientation=landscape', headers={
            'Authorization': f'Client-ID {self.bot.config["SECRET"]["unsplash"]}'
        })
        rawImage = requests.get(imageData.json()["urls"]["raw"]).content
        image = Image.open(io.BytesIO(rawImage))
        image.resize((1920,1080),Image.ANTIALIAS)
        image = image.filter(ImageFilter.GaussianBlur(radius=10))
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("Ubuntu-Light.ttf", 100)
        margin = offset = image.width/4
        for line in textwrap.wrap(quote.json()['content'], width=40):
            draw.text((margin, offset), line, font=font, fill=(255, 255, 255))
            offset += font.getsize(line)[1]

        # Write the quote author
        font = ImageFont.truetype("Ubuntu-Light.ttf", 64)
        draw.text(((image.width/4)*3,offset), quote.json()['author'], font=font, fill=(255, 255, 255), align="right")
        image.save(f'{(quote.json()["content"][:75] + "..") if len(quote.json()["content"]) > 75 else quote.json()["content"]}.jpg', quality=75)
        await context.send(file=discord.File(f'{(quote.json()["content"][:75] + "..") if len(quote.json()["content"]) > 75 else quote.json()["content"]}.jpg'))
        

    
def setup(bot: Bot):
    bot.add_cog(Quotes(bot))