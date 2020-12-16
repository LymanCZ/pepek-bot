import asyncio
import ctypes
import os
import random

import discord
import youtube_dl
from discord.ext import commands
from googleapiclient.discovery import build

from cogs.garfield_cog import daily_garfield
from lib.emotes import basic_emoji

bot = commands.Bot(command_prefix='pp.')

# Bot's token
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Bot's discord activites
activites = [
    discord.Game(name="with křemík."),
    discord.Activity(type=discord.ActivityType.listening, name="frequencies."),
    discord.Activity(type=discord.ActivityType.watching, name="you.")
]

async def status_changer():
    while True:
        try:
            await bot.change_presence(activity=random.choice(activites))
        except:
            # Wait a little longer if a connection error occurs
            await asyncio.sleep(90)
        await asyncio.sleep(30)

# If bot restarted while it was connected to a voice channel, the bot doesn't actually go "offline" on Discord if it comes up online in a few seconds, so it doesn't get disconnected and attempting to connect while already connected yields an exception
async def leave_voice():
    for guild in bot.guilds:
        if guild.voice_client and guild.voice_client.is_connected():
            await guild.voice_client.disconnect()

# Runs only once when bot boots up, creates background tasks
@bot.event
async def on_ready():
    bot.loop.create_task(leave_voice())
    bot.loop.create_task(status_changer())
    bot.loop.create_task(daily_garfield(bot.guilds[0].text_channels[0]))

# Catches some errors that are a fault of the user to notify them
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.message.add_reaction(basic_emoji.get("Si"))
        await ctx.send("{0}📣 COMMAND NOT FOUND".format(basic_emoji.get("Pepega")))
    elif isinstance(error, commands.errors.NoPrivateMessage):
        await ctx.message.add_reaction(basic_emoji.get("Si"))
        await ctx.send("Not available in DMs.")
    elif isinstance(error, commands.errors.UnexpectedQuoteError):
        await ctx.message.add_reaction(basic_emoji.get("Si"))
        await ctx.send("{0}📣 UNEXPECTED QUOTE ERROR\nUse `\\` to escape your quote(s) {1}".format(basic_emoji.get("Pepega"), basic_emoji.get("forsenScoots")))
    else:
        raise error


bot.load_extension("cogs.music_cog")
bot.load_extension("cogs.garfield_cog")
bot.load_extension("cogs.miscellaneous_cog")
bot.load_extension("cogs.utility_cog")
bot.run(DISCORD_TOKEN)
