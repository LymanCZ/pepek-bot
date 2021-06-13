import asyncio
import ctypes
import random
from textwrap import wrap

import discord
from discord.ext import commands

from lib.discord_session import Session
from lib.discord_session import Player
from lib.emotes import basic_emoji, dance_emoji, dance_react
from lib.youtube_tools import select_video


class Music(commands.Cog):
    """Everything related to playing music"""

    def __init__(self, bot):
        self.bot = bot
        self.sessions = dict()
        for guild in self.bot.guilds:
            self.sessions[guild.id] = Session()

        # Load library to be able to transmit audio packets
        discord.opus.load_opus(ctypes.util.find_library("opus"))

    @commands.command(name="play", aliases=["resume", "unpause"], help="Join VC and play music.")
    @commands.guild_only()
    async def play(self, ctx, *args):
        """Play or resume music"""

        session = self.sessions[ctx.guild.id]

        # No arguments and nothing is playing -> exit
        if not args and (session.vc is None or not session.vc.is_paused()):
            await ctx.send("Play what? " + basic_emoji.get("Pepega") + basic_emoji.get("Clap") + "\n" + basic_emoji.get("forsenSmug"))
            await ctx.message.add_reaction(basic_emoji.get("Si"))
            return

        # Get voice channel
        try:
            channel = ctx.author.voice.channel

        # User not connected to voice channel -> exit
        except AttributeError:
            msg = await ctx.send("You're not connected to a voice channel.")
            await msg.add_reaction(basic_emoji.get("Si"))
            return

        # Bot is missing permissions
        if not channel.permissions_for(ctx.guild.get_member(self.bot.user.id)).connect:
            await ctx.send("🔒 I don't have permission to join that channel " + basic_emoji.get("Pepega"))
            return
        if not channel.permissions_for(ctx.guild.get_member(self.bot.user.id)).speak:
            await ctx.send("🔒 I don't have permission to speak in that channel " + basic_emoji.get("Pepega"))
            return

        # Resume if paused and no song requested
        if not args and session.is_paused():
            session.resume()
            await ctx.send("Resumed playing " + random.choice(dance_emoji))
            return

        # Extract youtube video url
        arg = " ".join(str(i) for i in args)
        url = await select_video(self.bot, ctx, arg)

        # No video selected by user
        if not url:
            return

        await session.connect(channel)

        # Add song to queue
        session.song_queue.append(url)
        if session.vc.is_playing():
            await ctx.send("Song added to queue.")
            return

        while session.song_queue:
            # Bot kicked from channel
            if session.vc is None or not session.vc.is_connected():
                session.reset()
                await ctx.send("Kicked from voice channel " + basic_emoji.get("FeelsWeirdMan") + " 🖕")
                return

            session.song = session.song_queue.pop(0)
            # Attempt to download video
            try:
                status = await ctx.send("Downloading... " + basic_emoji.get("docSpin"))
                player = await asyncio.wait_for(Player.from_url(session.song, loop=self.bot.loop), timeout=120)

            # Timed out
            except asyncio.TimeoutError:
                await status.delete()
                await ctx.send("Download timed out (120 seconds), `" + session.song + "` skipped " + basic_emoji.get("Si"))
                continue

            # Other exception
            except:
                await status.delete()
                await ctx.send("Download failed (possibly age-restricted video), `" + session.song + "` skipped " + basic_emoji.get("Si"))
                continue

            await status.delete()

            # Bot kicked from vc while downloading -> return to "empty" state (no vc, nothing queued)
            if session.vc is None or not session.vc.is_connected():
                session.reset()
                await ctx.send("Kicked from voice channel " + basic_emoji.get("FeelsWeirdMan") + " 🖕")
                return

            session.vc.play(player)
            title = await ctx.send(random.choice(dance_emoji) + " 🎶 Now playing 🎶: `" + player.title + "` " + random.choice(dance_emoji))
            await title.add_reaction(random.choice(dance_react))

            while (session.vc.is_playing() or session.vc.is_paused()) and session.vc.is_connected():
                await asyncio.sleep(1)

            while session.repeat and session.vc.is_connected():
                session.vc.play(player.revive(player))
                while (session.vc.is_playing() or session.vc.is_paused()) and session.vc.is_connected():
                    await asyncio.sleep(1)

        # Bot kicked from vc while playing
        if not session.vc.is_connected():
            session.reset()
            await ctx.send("Kicked from voice channel " + basic_emoji.get("FeelsWeirdMan") + " 🖕")
            return

        # Leave voice after last song
        await session.vc.disconnect()
        session.reset()

    @commands.command(name="forceplay", aliases=["priorityplay"], help="Add song to the front of the queue.")
    @commands.guild_only()
    async def forceplay(self, ctx, *args):
        """Put song in front of queue"""

        session = self.sessions[ctx.guild.id]

        # No arguments -> exit
        if not args:
            await ctx.send("Play what? " + basic_emoji.get("Pepega") + basic_emoji.get("Clap") + "\n" + basic_emoji.get("forsenSmug"))
            await ctx.message.add_reaction(basic_emoji.get("Si"))
            return

        if session.vc is None:
            await ctx.send("Nothing is queued to skip in front of " + basic_emoji.get("Pepega") + basic_emoji.get("Clap") + "\nUse `p.play`")
            await ctx.message.add_reaction(basic_emoji.get("Si"))
            return

        # Extract youtube video url
        arg = " ".join(str(i) for i in args)
        url = await select_video(self.bot, ctx, arg)

        # No video selected by user
        if not url:
            return

        session.forceplay(url)
        await ctx.send("Song inserted to the front of the queue.")

    @commands.command(name="queue", help="Display songs in queue.")
    @commands.guild_only()
    async def queue(self, ctx):
        """Display queue"""

        session = self.sessions[ctx.guild.id]

        for segment in wrap(session.queue_to_string(), 1995):
            await ctx.send(segment)

    @commands.command(name="clear", help="Clear song queue.")
    @commands.guild_only()
    async def clear(self, ctx):
        """Clear song queue"""

        session = self.sessions[ctx.guild.id]

        if not session.song_queue:
            await ctx.send("Queue already empty " + basic_emoji.get("forsenScoots"))
            return

        session.song_queue = []
        await ctx.send("Queue emptied.")

    @commands.command(name="skip", aliases=["next"], help="Skip current song.")
    @commands.guild_only()
    async def skip(self, ctx):
        """Play next song in queue"""

        session = self.sessions[ctx.guild.id]

        if not session.next_song():
            msg = await ctx.send("Nothing is playing.")
            await msg.add_reaction(basic_emoji.get("Si"))

    @commands.command(name="pause", help="Pause music.")
    @commands.guild_only()
    async def pause(self, ctx):
        """Pause current song"""

        session = self.sessions[ctx.guild.id]

        if session.vc.pause():
            msg = await ctx.send("Nothing is playing.")
            await msg.add_reaction(basic_emoji.get("Si"))

        else:
            await ctx.send(basic_emoji.get("residentCD") + " Paused " + basic_emoji.get("Okayga"))

    @commands.command(name="repeat", aliases=["toggle_repeat", "stop_repeat"], help="Repeat current song.")
    @commands.guild_only()
    async def repeat(self, ctx):
        """Toggle repeat"""

        session = self.sessions[ctx.guild.id]

        if not session.song:
            msg = await ctx.send("Nothing is playing.")
            await msg.add_reaction(basic_emoji.get("Si"))
            return

        session.repeat = not session.repeat
        await ctx.send("Repeat set to `{0}`".format(session.repeat))

    @commands.command(name="stop", aliases=["leave"], help="Stop playing and leave voice channel.")
    @commands.guild_only()
    async def stop(self, ctx):
        """Stop playback"""

        session = self.sessions[ctx.guild.id]

        if not session.stop():
            msg = await ctx.send("Nothing is playing.")
            await msg.add_reaction(basic_emoji.get("Si"))

    @commands.command(name="playing", aliases=["song"], help="Display currently playing song.")
    @commands.guild_only()
    async def playing(self, ctx):
        """Display currently playing song"""

        session = self.sessions[ctx.guild.id]

        if not session.song:
            msg = await ctx.send("Nothing is playing.")
            await msg.add_reaction(basic_emoji.get("Si"))

        else:
            title = await ctx.send(random.choice(dance_emoji) + " 🎶 Now playing 🎶: " + session.song)
            await title.add_reaction(random.choice(dance_react))


def setup(bot):
    bot.add_cog(Music(bot))
