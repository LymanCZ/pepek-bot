import datetime
import random
from datetime import datetime
from typing import Union

import discord
from discord.ext import commands

from lib.emotes import basic_emoji


class Miscellaneous(commands.Cog):
    """Other interesting commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping", help="Display bot's ping.")
    async def ping(self, ctx):
        """Displays time delta between Discord message and command invocation"""

        ms = (datetime.utcnow() - ctx.message.created_at).total_seconds() * 1000
        await ctx.send(basic_emoji.get("Pepega") + " 🏓 Pong! `{0}ms`".format(int(ms)))

    @commands.command(name="roll", help="Generate a random number between 1 and 100 by default.")
    async def roll(self, ctx, num: str = "100"):
        """Roll a dice"""

        # Default string for invalid input
        result = "No, I don't think so. " + basic_emoji.get("forsenSmug")

        # Parse input
        if num.isnumeric():
            # Roll dice
            result = str(random.randint(1, int(num)))
        else:
            await ctx.message.add_reaction(basic_emoji.get("Si"))

        # Display result
        await ctx.send(result)

    @commands.command(name="decide", aliases=["choose"], help="Decide between options.")
    async def decide(self, ctx, *args):
        """Choose one option from a list"""

        # No arguments -> exit
        if not args:
            await ctx.send("Decide between what? " + basic_emoji.get("Pepega") + basic_emoji.get("Clap") + "\nUse `;`, `:`, `,` or ` or `, to separate options.")
            await ctx.message.add_reaction(basic_emoji.get("Si"))
            return

        # Join arguments to one string
        raw = " ".join(str(i) for i in args)

        # Attempt to split it by any separator
        options = raw.split(";")
        if len(options) < 2:
            options = raw.split(":")
            if len(options) < 2:
                options = raw.split(",")
                if len(options) < 2:
                    options = raw.split(" or ")

        # Splitting failed
        if len(options) < 2:
            await ctx.send("Separator not recognized, use `;`, `:`, `,` or ` or `, to separate options.")

        # Else send a result
        else:
            await ctx.send(random.choice(options))

    @commands.command(name="created", help="Find when an account was created")
    async def created(self, ctx, user: Union[discord.Member, discord.User, discord.ClientUser, str, None]):
        """Display account creation date"""

        if isinstance(user, str):
            await ctx.send("Try a user's tag instead " + basic_emoji.get("Okayga"))
            return

        if user is None:
            user_id = ctx.author.id
            msg = "Your account"
        else:
            user_id = user.id
            msg = "That account"

        # Decode user's ID
        binary = str(bin(user_id)[2:])
        unix_binary = binary[:len(binary) - 22]
        unix = (int(unix_binary, 2) + 1420070400000) // 1000

        time = datetime.utcfromtimestamp(unix).strftime("%Y-%m-%d %H:%M:%S")

        await ctx.send("{0} was created at {1} UTC".format(msg, time))


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
