######################################################
###                   DISCLAIMER                   ###
###                                                ###
###       This cog hasn't been rewritten yet       ###
###                                                ###
######################################################

import asyncio
import ctypes
import os
import random

import discord
import youtube_dl
from discord.ext import commands
from googleapiclient.discovery import build

from lib.emotes import basic_emoji, dance_emoji, dance_react
from lib.config import ffmpeg_options, ytdl_format_options

from main import bot as bot_internal

# Youtube search
YOUTUBE_API_TOKEN = os.getenv("YOUTUBE_API_TOKEN")

# Used when looking up videos
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_TOKEN)
# To be able to transmit audio packets (music)
discord.opus.load_opus(ctypes.util.find_library("opus"))
# https://stackoverflow.com/questions/56060614/how-to-make-a-discord-bot-play-youtube-audio
youtube_dl.utils.bug_reports_message = lambda: ''

# Used to download youtube videos
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Variables related to playing music (this is awful and will only ever work if the bot is used just on ONE server, since interactions on one server influence it globally)
# Voice chat
vc = None
# Queued songs (youtube URLs)
song_queue = []
# Currently playing song
song = ""
# If true will repeat last song
repeat_song = False
# Keeps downloaded data of last song (used when repeating in order to not download same song repeatedly)
ytdlData = None


# Returns a list of videos found with title query
def youtube_search(title):
    search_response = youtube.search().list(q=title, part="id,snippet", maxResults=10).execute()
    videos = []

    # Parse response
    for search_result in search_response.get("items", []):
        # Only take videos (not channels or playlists)
        if search_result["id"]["kind"] == "youtube#video":
            # Add pairs of ('title - [channel]' : 'video_id') to list
            videos.append(("`{0}` - `[{1}]`".format(search_result["snippet"]["title"], search_result["snippet"]["channelTitle"]), search_result["id"]["videoId"]))

        # Stop at 5
        if len(videos) == 5:
            return videos
    return videos


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data
        global ytdlData
        ytdlData = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    def revive(cls):
        global ytdlData
        filename = ytdlData['url']
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=ytdlData)

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # Take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


async def youtubeURLextractor(ctx, arg):
    # URL contained in argument
    if 'youtube.com/watch?v=' in arg or 'youtu.be/' in arg:
        # Assuming it's the first 'word' of argument
        return arg.partition(' ')[0]
    # Else search youtube for video title
    else:
        videos = []
        try:
            videos = youtube_search(arg)
        except:
            msg = await ctx.send(basic_emoji.get('hackerCD') + 'HTTP error. ' + basic_emoji.get('Sadge'))
            await msg.add_reaction(basic_emoji.get('Si'))
            return ""
        # 0 videos -> exit
        if len(videos) == 0:
            msg = await ctx.send('0 videos found. ' + basic_emoji.get('Sadge'))
            await msg.add_reaction(basic_emoji.get('Si'))
            return ""
        # 1 video -> we have a winner
        elif len(videos) == 1:
            return 'https://www.youtube.com/watch?v=' + videos[0][1]
        # Else let user to choose which one they meant
        else:
            poll = ''
            i = 0
            # Only giving 5 choices max
            number_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
            valid_numbers = []
            # Iterate over all (5 at most) found videos, pair = ('title - channel' : 'video_id')
            for pair in videos:
                # Add title to message
                poll += number_emojis[i] + '. ' + pair[0] + '\n'
                # Add valid option
                valid_numbers.append(number_emojis[i])
                i += 1
            # Display message with available videos
            msg = await ctx.send(poll)

            # Add options
            for number in valid_numbers:
                await msg.add_reaction(number)
            await msg.add_reaction('❌')

            # Checks if added reaction is the one we're waiting for
            def check(reaction, user):
                return user == ctx.message.author and (str(reaction.emoji) in valid_numbers or str(reaction.emoji) == '❌')

            reaction = None
            try:
                # Watch for reaction
                reaction, user = await bot_internal.wait_for('reaction_add', timeout=120, check=check)
            except asyncio.TimeoutError:
                await ctx.send('No option chosen (timed out) ' + basic_emoji.get('Si'))
                await msg.delete()
                return ""
            # Create chosen URL
            else:
                if str(reaction.emoji) == '❌':
                    await msg.delete()
                    return ""
                await msg.delete()
                return 'https://www.youtube.com/watch?v=' + videos[valid_numbers.index(str(reaction.emoji))][1]


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Play a requested song or resume paused queue
    # This works properly only on one server at a time
    # That's fine since this bot is a 'private' one, only made for one server
    @commands.command(name='play', aliases=['resume', 'unpause'], help="Join VC and play music.")
    @commands.guild_only()
    async def play(self, ctx, *args):
        global vc
        # No arguments -> exit
        if not args and (vc is None or not vc.is_paused()):
            await ctx.send("Play what? " + basic_emoji.get('Pepega') + basic_emoji.get('Clap') + '\n' + basic_emoji.get('forsenSmug'))
            await ctx.message.add_reaction(basic_emoji.get('Si'))
            return

        # Get voice channel
        channel = None
        try:
            channel = ctx.author.voice.channel
        # User not connected to voice channel -> exit
        except:
            msg = await ctx.send("You're not connected to a voice channel.")
            await msg.add_reaction(basic_emoji.get('Si'))
            return

        if not channel.permissions_for(ctx.guild.get_member(self.bot.user.id)).connect:
            await ctx.send("🔒 I don't have permission to join that channel " + basic_emoji.get('Pepega'))
            return

        if not channel.permissions_for(ctx.guild.get_member(self.bot.user.id)).speak:
            await ctx.send("🔒 I don't have permission to speak in that channel " + basic_emoji.get('Pepega'))
            return

        # Resume if paused and no song requested
        if not args and vc.is_paused():
            vc.resume()
            await ctx.send('Resumed playing ' + random.choice(dance_emoji))
            return

        # Extract youtube video url
        arg = ' '.join(str(i) for i in args)
        url = await youtubeURLextractor(ctx, arg)
        if not url:
            return

        if vc is None:
            vc = await channel.connect()
        else:
            await vc.move_to(channel)

        global song_queue
        song_queue.append(url)
        if vc.is_playing():
            await ctx.send('Song added to queue.')
            return

        global song
        global repeat_song
        while song_queue:
            # Bot kicked from channel
            if not vc.is_connected():
                vc = None
                queue = []
                song = ""
                repeat_song = False
                await ctx.send('Kicked from voice channel ' + basic_emoji.get('FeelsWeirdMan') + ' 🖕')
                return

            song = song_queue.pop(0)
            player = None
            status = None
            # Attempt to download video
            try:
                status = await ctx.send('Downloading... ' + basic_emoji.get('docSpin'))
                # 30 sec timeout (stops 10 hour videos)
                player = await asyncio.wait_for(YTDLSource.from_url(song, loop=self.bot.loop), timeout=120)
            except asyncio.TimeoutError:
                await status.delete()
                await ctx.send('Download timed out (120 seconds), `' + song + '` skipped ' + basic_emoji.get('Si'))
                continue
            except:
                await status.delete()
                await ctx.send('Download failed (possibly age-restricted video), `' + song + '` skipped ' + basic_emoji.get('Si'))
                continue

            await status.delete()

            # Bot kicked from vc while downloading -> return to "empty" state (no vc, nothing queued)
            if vc is None or not vc.is_connected():
                vc = None
                queue = []
                song = ""
                repeat_song = False
                await ctx.send('Kicked from voice channel ' + basic_emoji.get('FeelsWeirdMan') + ' 🖕')
                return

            vc.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
            title = await ctx.send(random.choice(dance_emoji) + ' 🎶 Now playing 🎶: `' + player.title + '` ' + random.choice(dance_emoji))
            await title.add_reaction(random.choice(dance_react))

            while (vc.is_playing() or vc.is_paused()) and vc.is_connected():
                await asyncio.sleep(1)

            while repeat_song and vc.is_connected():
                vc.play(player.revive(), after=lambda e: print('Player error: %s' % e) if e else None)
                while (vc.is_playing() or vc.is_paused()) and vc.is_connected():
                    await asyncio.sleep(1)

        # Bot kicked from vc while playing
        if not vc.is_connected():
            vc = None
            queue = []
            song = ""
            repeat_song = False
            await ctx.send('Kicked from voice channel ' + basic_emoji.get('FeelsWeirdMan') + ' 🖕')
            return

        # Leave voice after last song
        await vc.disconnect()
        vc = None
        song = ""

    @commands.command(name='forceplay', aliases=['priorityplay'], help="Add song to the front of the queue.")
    @commands.guild_only()
    async def forceplay(self, ctx, *args):
        # No arguments -> exit
        if not args:
            await ctx.send("Play what? " + basic_emoji.get('Pepega') + basic_emoji.get('Clap') + '\n' + basic_emoji.get('forsenSmug'))
            await ctx.message.add_reaction(basic_emoji.get('Si'))
            return

        global vc
        if vc is None:
            await ctx.send("Nothing is queued to skip in front of " + basic_emoji.get('Pepega') + basic_emoji.get('Clap') + "\nUse `p.play`")
            await ctx.message.add_reaction(basic_emoji.get('Si'))
            return

        # Extract youtube video url
        arg = ' '.join(str(i) for i in args)
        url = await youtubeURLextractor(ctx, arg)
        if not url:
            return

        global song_queue
        song_queue.insert(0, url)
        await ctx.send('Song inserted to the front of the queue.')

    @commands.command(name='queue', help="Display songs in queue.")
    @commands.guild_only()
    async def queue(self, ctx):
        global song_queue
        if not song_queue:
            await ctx.send('Queue is empty.')
            return
        msg = ""
        for song in song_queue:
            msg += song + '\n'
        await ctx.send('🎶 Queue 🎶: ' + msg[:1980])

    @commands.command(name='clear', help="Clear song queue.")
    @commands.guild_only()
    async def clear(self, ctx):
        global song_queue
        if not song_queue:
            await ctx.send('Queue already empty ' + basic_emoji.get('forsenScoots'))
            return
        song_queue = []
        await ctx.send('Queue emptied.')

    @commands.command(name='skip', aliases=['next'], help="Skip current song.")
    @commands.guild_only()
    async def skip(self, ctx):
        global vc
        global song
        global repeat_song
        try:
            vc.stop()
            song = ""
            repeat_song = False
        except:
            msg = await ctx.send("Nothing is playing.")
            await msg.add_reaction(basic_emoji.get('Si'))

    @commands.command(name='pause', help="Pause music.")
    @commands.guild_only()
    async def pause(self, ctx, *args):
        global vc
        try:
            vc.pause()
            await ctx.send(basic_emoji.get('residentCD') + ' Paused ' + basic_emoji.get('Okayga'))
        except:
            msg = await ctx.send("Nothing is playing.")
            await msg.add_reaction(basic_emoji.get('Si'))

    @commands.command(name='repeat', aliases=['toggle_repeat', 'stop_repeat'], help="Repeat current song.")
    @commands.guild_only()
    async def repeat(self, ctx):
        global song
        if not song:
            msg = await ctx.send("Nothing is playing.")
            await msg.add_reaction(basic_emoji.get('Si'))
            return

        global repeat_song
        repeat_song = not repeat_song
        await ctx.send("Repeat set to `{0}`".format(repeat_song))

    @commands.command(name='stop', aliases=['leave'], help="Stop playing and leave voice channel.")
    @commands.guild_only()
    async def stop(self, ctx):
        global vc
        global song_queue
        global song
        global repeat_song
        song_queue = []
        song = ""
        repeat_song = False
        try:
            vc.stop()
        except:
            msg = await ctx.send("Nothing is playing.")
            await msg.add_reaction(basic_emoji.get('Si'))

    @commands.command(name='playing', aliases=['song'], help="Display currently playing song.")
    @commands.guild_only()
    async def playing(self, ctx):
        global song
        if not song:
            msg = await ctx.send("Nothing is playing.")
            await msg.add_reaction(basic_emoji.get('Si'))
        else:
            title = await ctx.send(random.choice(dance_emoji) + ' 🎶 Now playing 🎶: ' + song)
            await title.add_reaction(random.choice(dance_react))


def setup(bot):
    bot.add_cog(Music(bot))
