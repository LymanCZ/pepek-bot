import asyncio
import os
import random

import discord
from discord.ext import commands
from pretty_help import PrettyHelp

from cogs.garfield_cog import daily_garfield
from lib.emotes import basic_emoji
from lib.config import activities


# Bot's token
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

bot = commands.Bot(command_prefix="p.")
bot.help_command = PrettyHelp(color=discord.Color.dark_red())


async def status_changer():
    """Changes bot's activity every so often"""

    while True:
        try:
            await bot.change_presence(activity=random.choice(activities))

        # Connection issue -> wait a little longer
        except discord.HTTPException:
            await asyncio.sleep(90)

        await asyncio.sleep(30)


async def leave_voice():
    """Disconnect from all voice channels"""

    for guild in bot.guilds:
        if guild.voice_client and guild.voice_client.is_connected():
            await guild.voice_client.disconnect()


@bot.event
async def on_ready():
    """Executed on startup"""

    bot.load_extension("cogs.fun_cog")
    bot.load_extension("cogs.games_cog")
    bot.load_extension("cogs.garfield_cog")
    bot.load_extension("cogs.miscellaneous_cog")
    bot.load_extension("cogs.utility_cog")
    bot.load_extension("cogs.music_cog")

    # Daily Garfield post
    bot.loop.create_task(daily_garfield(bot.guilds[0].text_channels[0]))

    # Activities
    bot.loop.create_task(status_changer())

    # Disconnect from all voice channels (if bot restarted, for example - that doesn't necessarily remove it from VC, have to do that manually)
    bot.loop.create_task(leave_voice())


@bot.event
async def on_command_error(ctx, error):
    """Executed when an exception is raised"""

    # Unknown command
    if isinstance(error, commands.CommandNotFound):
        await ctx.message.add_reaction(basic_emoji.get("Si"))
        await ctx.send("{0}📣 COMMAND NOT FOUND".format(basic_emoji.get("Pepega")))

    # Limited command in DMs
    elif isinstance(error, commands.errors.NoPrivateMessage):
        await ctx.message.add_reaction(basic_emoji.get("Si"))
        await ctx.send("Not available in DMs.")

    # Unescaped quotes
    elif isinstance(error, commands.errors.UnexpectedQuoteError):
        await ctx.message.add_reaction(basic_emoji.get("Si"))
        await ctx.send("{0}📣 UNEXPECTED QUOTE ERROR\nUse `\\` to escape your quote(s) {1}".format(basic_emoji.get("Pepega"), basic_emoji.get("forsenScoots")))

    # Command cooldown
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.message.add_reaction(basic_emoji.get("Si"))
        await ctx.send("That command is on cooldown.")
        
    else:
        raise error


bot.run(DISCORD_TOKEN)
