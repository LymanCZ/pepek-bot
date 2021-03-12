import datetime
import random
from textwrap import wrap
from typing import Union

import basc_py4chan
import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import commands

from lib.config import headers
from lib.datetime_lib import random_date, custom_strftime
from lib.emotes import basic_emoji, scoots_emoji
from lib.wiki_fact import get_day_fact, WikipediaError


class Fun(commands.Cog):
    """Fun commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="deth", aliases=["death"], help="Find out when you or someone else will die.")
    async def deth(self, ctx, user: Union[discord.User, str, None]):
        """Displays random but consistent string"""

        # Set seed (consistent RNG everytime for given user / input)
        if not user:
            # No input provided -> use caller
            random.seed(ctx.message.author.id)
            name = "You"
        elif isinstance(user, discord.User):
            # User tag provided
            random.seed(user.id)
            name = user.display_name
        elif isinstance(user, discord.ClientUser):
            # Bot tag provided (bots are ClientUser class, regular users are User class)
            random.seed(user.id)
            name = user.name
        else:
            # Some other string provided
            random.seed(abs(hash(user.lower())))
            name = user

        causes = ["cardiovascular disease", "cancer", "dementia", "diarrheal disease", "tuberculosis", "malnutrition", "HIV/AIDS", "malaria", "smoking", "suicide", "homicide", "natural disaster", "road incident", "drowning", "fire", "terrorism", "death by animal", "death by poison", "death by pufferfish", "death by sauna", "death by electrocution", "crushed by murphy bed"]

        date = random_date(datetime.date(2025, 1, 1), datetime.date(2100, 1, 1))
        await ctx.send("{0} will die on {1}. Cause of deth: {2}.".format(name, custom_strftime("%B {S}, %Y", date), random.choice(causes)))

        # Reseed RNG (other things use the same generator, avoids being manipulable)
        random.seed()

    @commands.command(name="fact", help="Get random fact about a day.")
    async def fact(self, ctx, arg1: str = "", arg2: str = ""):
        """Displays a random interesting fact"""

        # No date provided -> use today's date
        if not arg1 or not arg2:
            date = datetime.datetime.today()
            msg = "On this day in the year "

        # Invalid date input -> stop
        elif not arg1.isnumeric() or not arg2.isnumeric():
            await ctx.send("That's not even a numeric date. Try something like '9 11'.")
            await ctx.message.add_reaction(basic_emoji.get("Si"))
            return

        # Attempt to parse date input
        else:
            try:
                date = datetime.date(2000, int(arg1), int(arg2))
                msg = "On " + custom_strftime("%B {S}", date) + " in the year "
            except ValueError:
                await ctx.send("No..? You must be using the wrong calendar. Try 'Month Day'.")
                await ctx.message.add_reaction(basic_emoji.get("Si"))
                return

        status = await ctx.send("Looking up an interesting fact... " + basic_emoji.get("docSpin"))

        # Try to find an interesting fact
        try:
            fact = get_day_fact(date)

        # Error -> stop
        except WikipediaError as e:
            await status.delete()
            await ctx.send(e)
            return

        await status.delete()
        response = await ctx.send(msg + fact)
        await response.add_reaction(random.choice(scoots_emoji))

    @commands.command(name="joke", aliases=["cringe"], help="Get a random joke")
    async def joke(self, ctx):
        """Display a random 'joke'"""

        url = "http://stupidstuff.org/jokes/joke.htm?jokeid={0}".format(random.randint(1, 3773))

        # Attempt to download webpage
        try:
            response = requests.get(url, headers)
            response.raise_for_status()
        except requests.HTTPError:
            fail = await ctx.send("Bad response (status code {0}) from {1})".format(response.status_code, url))
            await fail.add_reaction(basic_emoji.get("Si"))
            return

        # Look for a joke
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table", attrs={"class": "scroll"})

        # If element not found
        if not table:
            fail = await ctx.send("Joke not found on {0}".format(url))
            await fail.add_reaction(basic_emoji.get("Si"))
            return

        for row in table.findAll("tr"):
            # Send string with empty lines removed (split into smaller parts in case it is >2000 characters long)
            for segment in wrap(str(row.text).replace("\n\n", "\n"), 1990):
                await ctx.send(segment)
                
    @commands.command(name="cah", aliases=["Cyanide&Happiness"], help="Get a Cyanide & Happiness daily strip")
    async def cah(self, ctx):
        """Cyanide & Happiness daily strip"""

        url = "https://explosm.net/"

        # Attempt to download webpage
        try:
            response = requests.get(url, headers)
            response.raise_for_status()
        except requests.HTTPError:
            fail = await ctx.send("Bad response (status code {0}) from {1})".format(response.status_code, url))
            await fail.add_reaction(basic_emoji.get("Si"))
            return

        # Look for a strip
        soup = BeautifulSoup(response.content, "html.parser")
        cah_comic_link = soup.find(id='main-comic')['src'][2:].split('?', 1)[0]

        # If element not found
        if not cah_comic_link:
            fail = await ctx.send("Daily strip not found on {0}".format(url))
            await fail.add_reaction(basic_emoji.get("Si"))
            return
        
        await ctx.send(cah_comic_link)

    @commands.command(name="chan", aliases=["4chan"], help="Get a random 4chan/4channel post.")
    async def chan(self, ctx, board: str = "", arg: str = ""):
        """Display random post (image in spoiler)"""

        # If no board specified, or random one -> choose random board
        if not board or board.lower() == "random":
            board_list = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'gif', 'd', 'h', 'hr', 'k', 'm', 'o', 'p', 'r', 's', 't', 'u', 'v', 'vg', 'w', 'wg', 'i', 'ic', 'r9k', 'cm', 'hm', 'y', '3', 'adv', 'an', 'cgl', 'ck', 'co', 'diy', 'fa', 'fit', 'hc', 'int', 'jp', 'lit', 'mlp', 'mu', 'n', 'po', 'pol', 'sci', 'soc', 'sp', 'tg', 'toy', 'trv', 'tv', 'vp', 'wsg', 'x']
            board = random.choice(board_list)

        # Attempt to download board
        try:
            b = basc_py4chan.Board(board)
            threads = b.get_all_threads()

        # Invalid board specified (library uses requests)
        except requests.exceptions.HTTPError:
            msg = await ctx.send("`/{0}/` doesn't exist.".format(board))
            await msg.add_reaction(basic_emoji.get("Si"))
            return

        result = ""
        post = None

        # Finding a post with text
        if arg.lower() == "text" or arg.lower() == "txt":
            # Try a random one until successful
            while not post or not post.text_comment:
                thread = random.choice(threads)
                post = random.choice(thread.posts)
                result = post.text_comment

        # Finding a post with image
        elif arg.lower() == "image" or arg.lower() == "img":
            while not post or not post.has_file:
                thread = random.choice(threads)
                post = random.choice(thread.posts)
                # Put image in a spoiler
                result = "|| {0} ||\n{1}".format(post.file_url, post.text_comment)

        # If no option specified -> find a post with text, image optional
        else:
            while not post or not post.text_comment:
                thread = random.choice(threads)
                post = random.choice(thread.posts)
                if post.has_file:
                    result = "|| {0} ||\n{1}".format(post.file_url, post.text_comment)
                else:
                    result = post.text_comment

        # Split into smaller parts if a post is too long (>2000 characters)
        for segment in wrap(result, 1990):
            await ctx.send(segment)

    @commands.command(name="advice", help="Receive wisdom.")
    async def advice(self, ctx):
        """Display random advice"""

        advice = requests.get("https://api.adviceslip.com/advice").json()

        msg = await ctx.send(advice["slip"]["advice"])
        await msg.add_reaction(random.choice(scoots_emoji))


def setup(bot):
    bot.add_cog(Fun(bot))
