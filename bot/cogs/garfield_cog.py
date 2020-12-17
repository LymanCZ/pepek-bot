import datetime
import random

import asyncio
import discord
from discord.ext import commands

from lib.datetime_lib import random_date, custom_strftime
from lib.emotes import basic_emoji, scoots_emoji
from lib.garfield_strip import garfield_strip, GarfieldError
from lib.wiki_fact import get_day_fact, WikipediaError


async def verbose_garfield(ctx, date) -> None:
    """Send a Garfield strip, with status notification"""

    status = await ctx.send(basic_emoji.get("hackerCD") + " Searching for Garfield strip " + basic_emoji.get("docSpin"))

    try:
        comic = garfield_strip(date)
    except GarfieldError as e:
        await status.delete()
        await ctx.send(e)
        return

    await status.delete()
    await ctx.send(comic)


def next_garfield() -> datetime.timedelta:
    """Calculate timedelta between right now and next Garfield strip release"""

    now = datetime.datetime.utcnow()
    tomorrow = now + datetime.timedelta(days=1)

    # TODO: Add summer/wintertime offset
    return datetime.datetime.combine(tomorrow, datetime.time.min) - now + datetime.timedelta(hours=6, minutes=7)


async def daily_garfield(channel: discord.TextChannel):
    """Post Garfield comic when it comes out to a channel"""

    # Wait until next release
    await asyncio.sleep(next_garfield().total_seconds())

    # Post today's Garfield strip and wait 24 hours
    while True:
        await verbose_garfield(channel, datetime.datetime.utcnow())
        await asyncio.sleep(86400)


class Garfield(commands.Cog):
    """Everything related to Garfield comics"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="today", help="Get today's Garfield comic.")
    async def today(self, ctx):
        """Display today's Garfield strip"""

        now = datetime.datetime.utcnow()

        # If today's comic isn't out yet
        # TODO: Add summer/wintertime offset
        if now.hour < 6 or (now.hour == 6 and now.minute < 7):
            release = datetime.datetime(now.year, now.month, now.day, 6, 7, 0, 0)
            delta = (release - now)
            hours = delta.seconds // 3600 % 24
            minutes = delta.seconds // 60 % 60
            seconds = delta.seconds - hours * 3600 - minutes * 60
            await ctx.send("You will have to be patient, today's comic comes out in {0}:{1}:{2}.".format(str(hours).zfill(2), str(minutes).zfill(2), str(seconds).zfill(2)))
            return

        await verbose_garfield(ctx, now)

    @commands.command(name="yesterday", help="Get yesterday's Garfield comic.")
    async def yesterday(self, ctx):
        """Display yesterday's Garfield comic"""

        now = datetime.datetime.utcnow()
        await verbose_garfield(ctx, now - datetime.timedelta(days=1))

    @commands.command(name="tomorrow", help="Get tomorrow's Garfield comic? Unless??")
    async def tomorrow(self, ctx):
        """Display when tomorrow's Garfield comic comes out"""

        # Calculate timedelta
        delta = next_garfield()
        hours = delta.seconds // 3600 % 24
        minutes = delta.seconds // 60 % 60
        seconds = delta.seconds - hours * 3600 - minutes * 60

        # If next garfield actually comes out today, simply add 24 hours for tomorrow's
        now = datetime.datetime.utcnow()
        # TODO: Add summer/wintertime offset
        if now.hour < 6 or (now.hour == 6 and now.minute < 7):
            hours += 24

        await ctx.message.add_reaction(basic_emoji.get("Si"))
        await ctx.send("You will have to be patient, tomorrow's comic comes out in {0}:{1}:{2}.".format(str(hours).zfill(2), str(minutes).zfill(2), str(seconds).zfill(2)))

    @commands.command(name="random", help="Get random Garfield comic.")
    async def rand_date(self, ctx):
        """Display random Garfield strip + interesting fact about that day"""
        date = random_date(datetime.datetime(1978, 6, 19), datetime.datetime.utcnow())

        await verbose_garfield(ctx, date)

        status = await ctx.send("Looking up an interesting fact... " + basic_emoji.get("docSpin"))
        msg = "This comic came out in " + custom_strftime("%B {S}, %Y", date) + "."

        # Try to find an interesting fact
        try:
            fact = get_day_fact(date)

        # Error -> stop
        except WikipediaError as e:
            await status.delete()
            await ctx.send(msg + e.message)
            return

        await status.delete()
        response = await ctx.send(msg + " Also on this day in " + fact)
        await response.add_reaction(random.choice(scoots_emoji))

    @commands.command(name="garf", aliases=["garfield"], help="Get specific Garfield comic, format: 'Year Month Day'.")
    async def garf(self, ctx, arg1: str = "", arg2: str = "", arg3: str = ""):
        """Get specific Garfield comic"""

        # Parsing input
        if not arg1 or not arg2 or not arg3:
            await ctx.send(basic_emoji.get("forsenT") + " Date looks like 'Year Month Day', ie. '2001 9 11'.")
            await ctx.message.add_reaction(basic_emoji.get("Si"))
            return

        if not arg1.isnumeric() or not arg2.isnumeric() or not arg3.isnumeric():
            await ctx.send(basic_emoji.get("forsenT") + " That's not even a numeric date.")
            await ctx.message.add_reaction(basic_emoji.get("Si"))
            return

        # Construct date
        try:
            date = datetime.datetime(int(arg1), int(arg2), int(arg3))
        except ValueError:
            await ctx.send(basic_emoji.get("forsenSmug") + " No..? You must be using the wrong calendar.")
            await ctx.message.add_reaction(basic_emoji.get("Si"))
            return

        # Send comic strip
        await verbose_garfield(ctx, date)


def setup(bot):
    bot.add_cog(Garfield(bot))
