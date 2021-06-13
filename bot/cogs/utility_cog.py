import io
import json
import os
import urllib
from textwrap import wrap

import discord
import googletrans
import requests
from discord.ext import commands
from google.cloud import vision
from google.oauth2 import service_account

from lib.emoji import code_to_country
from lib.emotes import basic_emoji

# Openweathermap (weather)
WEATHER_TOKEN = os.getenv("WEATHER_TOKEN")
# WolframAlpha queries
WOLFRAM_APPID = os.getenv("WOLFRAM_APPID")
# Google cloud APIs (VisionAI - text OCR) - it's in JSON, instead of writing to file just parsing using json library
GOOGLE_CLOUD_CREDENTIALS = service_account.Credentials.from_service_account_info(json.loads(os.getenv("GOOGLE_CLIENT_SECRETS")))
# Used to read text from image
google_vision = vision.ImageAnnotatorClient(credentials=GOOGLE_CLOUD_CREDENTIALS)
# Used to translate text
translator = googletrans.Translator()


class ContentError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


def detect_text(url: str) -> str:
    """Uses Google Cloud VisionAI"""

    # Convert data to image
    image = vision.Image()
    image.source.image_uri = url
    response = google_vision.text_detection(image=image)

    # Invalid URL provided
    if response.error.message:
        raise ContentError("That's not an image? {0}{1}\n{2}".format(basic_emoji.get("Pepega"), basic_emoji.get("Clap"), basic_emoji.get("forsenSmug")))

    # Let VisionAI do its thing
    texts = response.text_annotations

    # Couldn't read anything
    if not texts:
        raise ContentError("Can't see shit! {0}".format(basic_emoji.get("forsenT")))

    # Return raw detected text
    return texts[0].description


class Utility(commands.Cog):
    """Reading text from image, translation, weather, calculator and more"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="read", help="Read image.")
    @commands.guild_only()
    async def read(self, ctx, url: str = ""):
        """Detect text in image"""

        # Check whether user provided url or embedded image
        if not url and not ctx.message.attachments:
            await ctx.send("Read what? " + basic_emoji.get("Pepega") + basic_emoji.get("Clap") + "\n" + basic_emoji.get("forsenSmug"))
            await ctx.message.add_reaction(basic_emoji.get("Si"))
            return

        # Get url to the image
        if not url:
            url = ctx.message.attachments[0].url

        # Display status
        status = await ctx.send("Processing... " + basic_emoji.get("docSpin"))

        # Attempt to detect text
        try:
            text = detect_text(url)
        except ContentError as e:
            await status.delete()
            await ctx.send(e)
            return

        await status.delete()
        # Split into short enough segments (Discord's max message length is 2000)
        for segment in wrap(text, 1990):
            await ctx.send("```" + segment + "```")

    @commands.command(name="translate", help="Translate text.")
    @commands.guild_only()
    async def translate(self, ctx, *, arg: str = ""):
        """Translate text"""

        # No text entered -> nothing to translate
        if not arg:
            await ctx.send("Translate what? " + basic_emoji.get("Pepega") + basic_emoji.get("Clap") + "\n" + basic_emoji.get("forsenSmug"))
            await ctx.message.add_reaction(basic_emoji.get("Si"))
            return

        # Split into ["first_word", "the_rest of the query"]
        query = arg.split(" ", 1)

        # If first word is an ISO639-1 language code, translate to that language
        if query[0] in googletrans.LANGUAGES:
            result = translator.translate(query[1], dest=query[0])

        # Otherwise translate to english by default
        else:
            result = translator.translate(arg, dest="en")

        # Using .lower() because for example chinese-simplified is 'zh-cn', but result.src returns 'zh-CN' (so dumb)
        header = "Translated from `{0}` {1} to `{2}` {3}".format(googletrans.LANGUAGES.get(result.src.lower()),
                                                                 code_to_country(result.src.lower()),
                                                                 googletrans.LANGUAGES.get(result.dest.lower()),
                                                                 code_to_country(result.dest.lower()))

        # Split into parts in case of very long translation
        first_iter = True
        for segment in wrap(result.text, 1950):
            # Send header together with the first part
            if first_iter:
                await ctx.send("{0}\n```{1}```".format(header, segment))
                first_iter = False
            # Send the rest parts standalone
            else:
                await ctx.send("```" + segment + "```")

    # Yoinked from https://github.com/Toaster192/rubbergod/blob/master/cogs/weather.py WideHard
    @commands.command(name="weather", help="Get location's weather.")
    async def weather(self, ctx, *args):
        """Get weather information"""

        # Default location
        location = "Prague"

        if args:
            location = " ".join(str(i) for i in args)

        url = ("http://api.openweathermap.org/data/2.5/weather?q=" + location + "&units=metric&lang=en&appid=" + WEATHER_TOKEN)
        res = requests.get(url).json()
        if str(res["cod"]) == "200":
            description = "Weather in " + res["name"] + " , " + res["sys"]["country"]
            embed = discord.Embed(title="Weather", description=description)
            image = "http://openweathermap.org/img/w/" + res["weather"][0]["icon"] + ".png"
            embed.set_thumbnail(url=image)
            weather = res["weather"][0]["main"] + " (" + res["weather"][0]["description"] + ") "
            temp = str(res["main"]["temp"]) + "°C"
            feels_temp = str(res["main"]["feels_like"]) + "°C"
            humidity = str(res["main"]["humidity"]) + "%"
            wind = str(res["wind"]["speed"]) + "m/s"
            clouds = str(res["clouds"]["all"]) + "%"
            visibility = str(res["visibility"] / 1000) + " km" if "visibility" in res else "no data"
            embed.add_field(name="Weather", value=weather, inline=False)
            embed.add_field(name="Temperature", value=temp, inline=True)
            embed.add_field(name="Feels like", value=feels_temp, inline=True)
            embed.add_field(name="Humidity", value=humidity, inline=True)
            embed.add_field(name="Wind", value=wind, inline=True)
            embed.add_field(name="Clouds", value=clouds, inline=True)
            embed.add_field(name="Visibility", value=visibility, inline=True)
            await ctx.send(embed=embed)
        elif str(res["cod"]) == "404":
            msg = await ctx.send("Location not found.")
            await msg.add_reaction(basic_emoji.get("Sadge"))
        elif str(res["cod"]) == "401":
            msg = await ctx.send("API key broke, have a nice day.")
            await msg.add_reaction(basic_emoji.get("Si"))
        else:
            await ctx.send("Location not found! " + basic_emoji.get("Sadge") + " (" + res["message"] + ")")

    @commands.command(name="wolfram", aliases=["wa", "wolframalpha", "wolfram_alpha"], help="WolframAlpha query.")
    @commands.guild_only()
    async def wolfram(self, ctx, *args):
        """Ask WolframAlpha a question"""

        # No arguments -> exit
        if not args:
            await ctx.send("What? " + basic_emoji.get('Pepega') + basic_emoji.get('Clap'))
            await ctx.message.add_reaction(basic_emoji.get('Si'))
            return

        # Parse query into url-friendly format (for example replaces spaces with '%2')
        query = urllib.parse.quote_plus(" ".join(str(i) for i in args))

        # Send query (with some extra arguments regarding result formatting)
        url = "http://api.wolframalpha.com/v1/simple?appid={0}&i={1}&background=36393f&foreground=white&timeout=30".format(WOLFRAM_APPID, query)

        async with ctx.typing():
            # Attempt to download result
            try:
                response = requests.get(url)
                response.raise_for_status()

            # Invalid query / timeout / something else
            except requests.HTTPError:
                fail = await ctx.send("Bad response (status code: {0})".format(response.status_code))
                await fail.add_reaction(basic_emoji.get("Si"))
                return

            # I want to send an image (generated by WolframAlpha), not embed a link (image would be regenerated if user clicked it + it would contain app_id)
            # And because discord.File has to open the file, I first save the file, then embed it, then delete it...
            # And to avoid overwriting during simultaneous calls, use the query's hash as the filename
            filename = "tmp" + str(hash(query))
            open(filename, "wb").write(response.content)

            await ctx.send(file=discord.File(filename, filename="result.png"))

            os.remove(filename)


def setup(bot):
    bot.add_cog(Utility(bot))
