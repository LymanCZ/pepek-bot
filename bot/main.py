import os
import io
import json
import random
import urllib
import ctypes
import asyncio
import discord
import datetime
import requests
import wikipedia
import youtube_dl
import googletrans
import emoji_locale
import basc_py4chan
from typing import Union
from typing import Optional
from textwrap import wrap
from bs4 import BeautifulSoup
from discord.ext import commands
from google.cloud import vision
from google.oauth2 import service_account
from googleapiclient.discovery import build

bot = commands.Bot(command_prefix='p.')

# Bot's token
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
# Openweathermap (weather)
WEATHER_TOKEN = os.getenv("WEATHER_TOKEN")
# Google cloud APIs (VisionAI - text OCR) - it's in JSON, instead of writing to file just parsing using json library
GOOGLE_CLOUD_CREDENTIALS = service_account.Credentials.from_service_account_info(json.loads(os.getenv("GOOGLE_CLIENT_SECRETS")))
# Youtube search
YOUTUBE_API_TOKEN = os.getenv("YOUTUBE_API_TOKEN")
# Log-in for youtube to download age-restricted videos ~this still doesn't solve the issue, I don't understand why~
YT_MAIL = os.getenv("YT_MAIL")
YT_PASS = os.getenv("YT_PASS")
# youtube-dl wants cookies as a text file ~this also doesn't solve the age-restriction issue~
with open("cookies.txt", "w") as text_file:
    print(os.getenv('COOKIE_DATA'), file=text_file)
# WolframAlpha queries
WOLFRAM_APPID = os.getenv("WOLFRAM_APPID")

# Used when looking up videos
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_TOKEN)
# Used to read text from image
google_vision = vision.ImageAnnotatorClient(credentials=GOOGLE_CLOUD_CREDENTIALS)
# Used to translate text
translator = googletrans.Translator()
# To be able to transmit audio packets (music)
discord.opus.load_opus(ctypes.util.find_library("opus"))
# https://stackoverflow.com/questions/56060614/how-to-make-a-discord-bot-play-youtube-audio
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    "cookies" : "cookies.txt",
    "user_agent" : "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0",
    "username" : YT_MAIL,
    "password" : YT_PASS,
    "format" : "bestaudio/best",
    "outtmpl" : "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames" : True,
    "noplaylist" : True,
    "nocheckcertificate" : True,
    "ignoreerrors" : False,
    "logtostderr" : False,
    "quiet" : True,
    "no_warnings" : True,
    "default_search" : "auto",
    "source_address" : "0.0.0.0" # Bind to IPv4 since IPv6 addresses cause issues sometimes
}
# Used to download youtube videos
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Used when converting downloaded videos (-vn discards video stream)
ffmpeg_options = {
    "options" : "-vn"
}

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

# Library of fun emojis used thorough
basic_emoji = {
    "Si" : "<:Si:523966164704034837>",
    "Sadge" : "<:Sadge:696437945392955453>",
    "Pepega" : "<:Pepega:739020602194657330>",
    "forsenSmug" : "<:forsenSmug:736973361283858442>",
    "forsenScoots" : "<:forsenScoots:736973346142552195>",
    "forsenT" : "<:forsenT:743128058545832048>",
    "docSpin" : "<a:docSpin:743133871889055774>",
    "hackerCD" : "<a:hackerCD:744835324827402250>",
    "Clap" : "<a:Clap:746628991753912401>",
    "FeelsWeirdMan" : "<:FeelsWeirdMan:750942213676073012>",
    "Okayga" : "<:Okayga:750974019104276521>",
    "residentCD" : "<:residentCD:750974439092518922>"
}
# Lists of different types of emojis used to choose a random one
scoots_emoji = [
    "<:forsenScoots:736973346142552195>",
    "<:OMGScoots:736973384570634321>"
]
dance_emoji = [
    "<a:forsenPls:741611256460476496>",
    "<a:forsenDiscoSnake:742013168234135664>",
    "<a:headBang:742013167890333802>",
    "<a:KKool:742013168196517899>" + " <a:GuitarTime:742013167554789390>",
    "<a:pepeJAM:742013167671967805>",
    "<a:AlienPls:742014131305054239>",
    "<a:SHUNGITE:744474032698556477> " + "<a:doctorDance:744473646298431510>" + " <a:SHUNGITE:744474032698556477>"
]
dance_react = [
    "<a:forsenPls:741611256460476496>",
    "<a:forsenDiscoSnake:742013168234135664>",
    "<a:headBang:742013167890333802>",
    "<a:KKool:742013168196517899>",
    "<a:pepeJAM:742013167671967805>",
    "<a:AlienPls:742014131305054239>",
    "<a:doctorDance:744473646298431510>"
]

# HTTP header used when looking up Garfield comic
headers = {
    "Access-Control-Allow-Origin" : "*",
    "Access-Control-Allow-Methods" : "GET",
    "Access-Control-Allow-Headers" : "Content-Type",
    "Access-Control-Max-Age" : "3600",
    "User-Agent" : "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0"
}

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
            await asyncio.asleep(90)
        await asyncio.sleep(30)
        
# Posts Garfield strip daily to a channel
async def daily_garfield():
    # Get time remaining until next release
    x = datetime.datetime.utcnow()
    y = x.replace(day=x.day, hour=6, minute=7)
    if not (x.hour < 6 or (x.hour == 6 and x.minute < 7)):
        y += datetime.timedelta(days=1)
    delta_t = y - x
    # Wait until then
    await asyncio.sleep(delta_t.total_seconds())
    # Afterwards, post today's Garfield strip and repeat every 24 hours
    while True:
        await garf_comic(bot.guilds[0].text_channels[0], datetime.datetime.utcnow())
        await asyncio.sleep(86400)

# If bot restarted while it was connected to a voice channel, the bot doesn't actually go "offline" on Discord if it comes up online in a few seconds, so it doesn't get disconnected and attempting to connect while already connected yields an exception
async def leave_voice():
    for guild in bot.guilds:
        if guild.voice_client and guild.voice_client.is_connected():
            await guild.voice_client.disconnect()

# Runs only once when bot boots up, creates background tasks
@bot.event
async def on_ready():
    bot.loop.create_task(status_changer())
    bot.loop.create_task(daily_garfield())
    bot.loop.create_task(leave_voice())

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
    
# Get a random datetime in range
def random_date(start, end):
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + datetime.timedelta(seconds=random_second)

# Time remaining until next Garfield strip comes out
def time_until_next_garfield():
    dt = datetime.datetime.utcnow()
    tomorrow = dt + datetime.timedelta(days=1)
    return datetime.datetime.combine(tomorrow, datetime.time.min) - dt + datetime.timedelta(hours=6, minutes=7)

# Format date to Garfield compatible (YYYY/MM/DD)
def format_date(date):
    return "{0}/{1}/{2}".format(str(date.year), str(date.month).zfill(2), str(date.day).zfill(2))

# Returns "st", "nd" or "rd" for a number
def suffix(n):
    return "th" if 11 <= n <= 13 else {1 : "st", 2 : "nd", 3 : "rd"}.get(n % 10, "th")
# Formats datetime using above function
def custom_strftime(format, date):
    return date.strftime(format).replace("{S}", str(date.day) + suffix(date.day))

# Uses Google Cloud VisionAI
def detect_text(url):
    # Download image from url
    response = requests.get(url)
    image = None
    try:
        # Convert data to image
        image_bytes = io.BytesIO(response.content)
        image = vision.types.Image(content=image_bytes.read())
    except:
        return "That's not an image? {0}{1}\n{2}".format(basic_emoji.get("Pepega"), basic_emoji.get("Clap"), basic_emoji.get("forsenSmug"))
    
    # Let VisionAI do its thing
    cloud_response = google_vision.text_detection(image=image)
    texts = cloud_response.text_annotations
    # Couldn't read anything
    if not texts:
        return "Can't see shit! {0}".format(basic_emoji.get("forsenT"))
    else:
        return texts[0].description
    
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

async def garf_comic(channel, date):
    link = "Something went wrong."
    # Construct URL using date
    url = "http://www.gocomics.com/garfield/" + format_date(date)
    status = await channel.send("{0} Sending HTTP request... {1}".format(basic_emoji.get("hackerCD"), basic_emoji.get("docSpin")))
    # GET page
    response = None
    try:
        response = requests.get(url, headers)
        response.raise_for_status()
    # Network error
    except:
        fail = await channel.send("Bad response (status code: {0}) from `{1}`".format(response.status_code, url))
        await status.delete()
        await fail.add_reaction(basic_emoji.get("Si"))
        return
    await status.edit(content="Parsing {0}kb... {1}".format(str(round((len(response.content)/1024.0),2)), basic_emoji.get("docSpin")))
    # Scrape page for comic
    soup = BeautifulSoup(response.content, "html.parser")
    await status.edit(content="Looking for Garfield comic...")
    picture = soup.find_all("picture", attrs={"class" : "item-comic-image"})
    # If not found (perhaps they changed how it's embedded)
    if not picture or not picture[0]:
        fail = await channel.send("Garfield comic not found on " + url)
        await status.delete()
        await fail.add_reaction(basic_emoji.get("Si"))
        return
    # Else send comic strip
    await status.edit(content="Garfield comic found.")
    link = picture[0].img["src"]
    await status.delete()
    
    await channel.send(link)

class Garfield(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="today", help="Get today's Garfield comic.")
    async def today(self, ctx):
        now = datetime.datetime.utcnow()
        # If today's comic isn't out yet
        if now.hour < 6 or (now.hour==6 and now.minute < 7):
            release = datetime.datetime(now.year, now.month, now.day, 5, 7, 0, 0)
            td = (release - now)
            hours = td.seconds // 3600 % 24
            minutes = td.seconds // 60 % 60
            seconds = td.seconds - hours*3600 - minutes*60
            await ctx.send("You will have to be patient, today's comic comes out in {0}:{1}:{2}.".format(str(hours).zfill(2), str(minutes).zfill(2), str(seconds).zfill(2)))
        else:
            await garf_comic(ctx.channel, now)

    @commands.command(name="yesterday", help="Get yesterdays's Garfield comic.")
    async def yesterday(self, ctx):
        now = datetime.datetime.utcnow()
        await garf_comic(ctx.channel, now - datetime.timedelta(days=1))

    @commands.command(name="tomorrow", help="Get tomorrow's Garfield comic? Unless??")
    async def tomorrow(self, ctx):
        td = time_until_next_garfield()
        hours = td.seconds // 3600 % 24
        now = datetime.datetime.utcnow()
        minutes = td.seconds // 60 % 60
        seconds = td.seconds - hours*3600 - minutes*60
        if now.hour < 6 or (now.hour==6 and now.minute < 7):
            hours += 24
        await ctx.message.add_reaction(basic_emoji.get("Si"))
        await ctx.send("You will have to be patient, tomorrow's comic comes out in {0}:{1}:{2}.".format(str(hours).zfill(2), str(minutes).zfill(2), str(seconds).zfill(2)))

    @commands.command(name="random", help="Get random Garfield comic.")
    async def rand_date(self, ctx):
        # Get a random day and that day's Garfield strip
        rd = random_date(datetime.date(1978, 6, 19), datetime.datetime.utcnow().date())
        await garf_comic(ctx.channel, rd)
        # Try to find an interesting fact about that day
        facts = None
        status = await ctx.send("Looking up an interesting fact... " + basic_emoji.get("docSpin"))
        fact = ""
        wiki_success = True
        try:
            fact = wikipedia.page(rd.strftime("%B") + " " + str(rd.day)).section("Events")
            await status.edit(content="Searching wikipedia.com/wiki/{0}_{1} for an interesting fact.".format(rd.strftime("%B"), str(rd.day)))
            facts = fact.splitlines()
        except:
            wiki_success = False
        if not wiki_success:
            await status.delete()
            fact = await ctx.send("Couldn't access wikipedia entry {0}\nThis comic came out in {1}.".format(basic_emoji.get("Pepega"), custom_strftime("%B {S}, %Y", rd)))
        elif not facts:
            await status.delete()
            fact = await ctx.send("Didn't find any interesting fact on wikipedia.com/wiki/{0}_{1}. Probably retarded formatting on this page for the 'events' section.".format(rd.strftime("%B"), str(rd.day), basic_emoji.get("Pepega")))
        else:
            await status.delete()
            fact = await ctx.send("This comic came out in {0}. On this day also in the year {1}".format(custom_strftime("%B {S}, %Y", rd), random.choice(facts).lstrip()))
            await fact.add_reaction(random.choice(scoots_emoji))

    @commands.command(name="garf", help="Get specific Garfield comic, format: 'Year Month Day'.")
    async def garf(self, ctx, arg1: str = "", arg2: str = "", arg3: str = ""):
        result = "No, I don't think so. " + basic_emoji.get("forsenSmug")
        # Parsing input..
        if not arg1 or not arg2 or not arg3:
            result = "Date looks like 'Year Month Day', ie. '2001 9 11' :)."
            await ctx.message.add_reaction(basic_emoji.get("Si"))
        elif not arg1.isnumeric() or not arg2.isnumeric() or not arg3.isnumeric():
            result = "That's not even a numeric date."
            await ctx.message.add_reaction(basic_emoji.get("Si"))
        else:
            a1 = int(arg1)
            a2 = int(arg2)
            a3 = int(arg3)
            correctDate = None
            newDate = None
            now = datetime.date.today()
            try:
                newDate = datetime.date(a1,a2,a3)
                correctDate = True
            except ValueError:
                correctDate = False
            if not correctDate:
                result = "No..? You must be using the wrong calendar."
                await ctx.message.add_reaction(basic_emoji.get("Si"))
            elif newDate > now:
                result = "You will have to wait for that day to come."
                await ctx.message.add_reaction(basic_emoji.get("Si"))
            elif newDate >= datetime.date(1978, 6, 19):
                result = ""
                # Correct date - sends Garfield strip
                await garf_comic(ctx.channel, datetime.date(a1, a2, a3))
            else:
                result = "Unfortunately, Garfield didn't exist before 19th June 1978."
                await ctx.message.add_reaction(basic_emoji.get("Si"))
        # Incorrect date - sends error message
        if result:
            await ctx.send(result)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data
        global ytdlData
        ytdlData = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    def revive(self):
        global ytdlData
        filename = ytdlData['url']
        return self(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=ytdlData)
        
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
                reaction, user = await bot.wait_for('reaction_add', timeout=120, check=check)               
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

        if not channel.permissions_for(ctx.guild.get_member(bot.user.id)).connect:
            await ctx.send("🔒 I don't have permission to join that channel " + basic_emoji.get('Pepega'))
            return

        if not channel.permissions_for(ctx.guild.get_member(bot.user.id)).speak:
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
                player = await asyncio.wait_for(YTDLSource.from_url(song, loop=bot.loop), timeout=120)
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
  
class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
                               
    @commands.command(name='read', help='Read image.')
    @commands.guild_only()
    async def read(self, ctx, url: str = ''):
        # Check whether user provided url or embedded image
        if not url and not ctx.message.attachments:
            await ctx.send("Read what? " + basic_emoji.get('Pepega') + basic_emoji.get('Clap') + '\n' + basic_emoji.get('forsenSmug'))
            await ctx.message.add_reaction(basic_emoji.get('Si'))
            return
        # Get url to the image
        if not url:
            url = ctx.message.attachments[0].url

        # Display status
        status = await ctx.send('Processing... ' + basic_emoji.get('docSpin'))
        # Attempt to detect text
        text = detect_text(url)
        await status.delete()
        # Split into short enough segments (Discord's max message length is 2000)
        for s in wrap(text, 1990):
            await ctx.send('```' + s + '```')

    @commands.command(name='translate', help="Translate text.")
    @commands.guild_only()
    async def translate(self, ctx, *, arg: str = ''):
        # No text entered -> nothing to translate
        if not arg:
            await ctx.send("Translate what? " + basic_emoji.get('Pepega') + basic_emoji.get('Clap') + '\n' + basic_emoji.get('forsenSmug'))
            await ctx.message.add_reaction(basic_emoji.get('Si'))
            return

        result = None
        # Combine tuple into one long string
        #arg = ' '.join(str(i) for i in args)
        # Get first word
        input = arg.split(' ', 1)
        # If it's an ISO639-1 language code, translate to that language
        if input[0] in googletrans.LANGUAGES:
            result = translator.translate(input[1], dest=input[0])
        # Otherwise translate to english by default
        else:
            result = translator.translate(arg, dest='en')

        # Using .lower() because for example chinese-simplified is 'zh-cn', but result.src would return 'zh-CN' (so dumb)
        msg = "Translated from `{0}` {1} to `{2}` {3}".format(googletrans.LANGUAGES.get(result.src.lower()), emoji_locale.code_to_country(result.src.lower()), googletrans.LANGUAGES.get(result.dest.lower()), emoji_locale.code_to_country(result.dest.lower()))
        # Remove any quotes from translated text (I couldn't figure out how to just escape them so discord wouldn't throw exceptions over un-quoted string or some shit)
        await ctx.send("{0}\n```{1}```".format(msg, result.text[:1950]))
                                
    # Yoinked from https://github.com/Toaster192/rubbergod/blob/master/cogs/weather.py WideHard
    @commands.command(name='weather', help="Get location's weather.")
    async def weather(self, ctx, *args):
        city = 'Prague'
        if args:
            city = ' '.join(str(i) for i in args)
        url = ('http://api.openweathermap.org/data/2.5/weather?q=' + city + '&units=metric&lang=en&appid=' + WEATHER_TOKEN)
        res = requests.get(url).json()
        if str(res['cod']) == '200':
            description = 'Weather in ' + res['name'] + ', ' + res['sys']['country']
            embed = discord.Embed(title='Weather', description=description)
            image = 'http://openweathermap.org/img/w/' + res['weather'][0]['icon'] + '.png'
            embed.set_thumbnail(url=image)
            weather = res['weather'][0]['main'] + ' (' + res['weather'][0]['description'] + ') '
            temp = str(res['main']['temp']) + '°C'
            feels_temp = str(res['main']['feels_like']) + '°C'
            humidity = str(res['main']['humidity']) + '%'
            wind = str(res['wind']['speed']) + 'm/s'
            clouds = str(res['clouds']['all']) + '%'
            visibility = str(res['visibility'] / 1000) + ' km' if 'visibility' in res else 'no data'
            embed.add_field(name='Weather', value=weather, inline=False)
            embed.add_field(name='Temperature', value=temp, inline=True)
            embed.add_field(name='Feels like', value=feels_temp, inline=True)
            embed.add_field(name='Humidity', value=humidity, inline=True)
            embed.add_field(name='Wind', value=wind, inline=True)
            embed.add_field(name='Clouds', value=clouds, inline=True)
            embed.add_field(name='Visibility', value=visibility, inline=True)
            await ctx.send(embed=embed)
        elif str(res['cod']) == '404':
            msg = await ctx.send('City not found.')
            await msg.add_reaction(basic_emoji.get('Sadge'))
        elif str(res['cod']) == '401':
            msg = await ctx.send('API key broke, have a nice day.')
            await msg.add_reaction(basic_emoji.get('Si'))
        else:
            await ctx.send('City not found! ' + basic_emoji.get('Sadge') + ' (' + res['message'] + ')')

    @commands.command(name='wolfram', aliases=['wa', 'wolframalpha', 'wolfram_alpha'], help="WolframAlpha query.")
    @commands.guild_only()
    async def wolfram(self, ctx, *args):
        # No arguments -> exit
        if not args:
            await ctx.send("What? " + basic_emoji.get('Pepega') + basic_emoji.get('Clap'))
            await ctx.message.add_reaction(basic_emoji.get('Si'))
            return

        # Parse query into url-friendly format (for example replaces spaces with '%2')
        query = urllib.parse.quote_plus(' '.join(str(i) for i in args))
        url = "http://api.wolframalpha.com/v1/simple?appid={0}&i={1}&background=36393f&foreground=white&timeout=30".format(WOLFRAM_APPID, query)

        async with ctx.typing():
            response = None
            try:
                response = requests.get(url)
                response.raise_for_status()
            except:
                fail = await ctx.send("Bad response (status code: {0})".format(response.status_code))
                await fail.add_reaction(basic_emoji.get('Si'))
                return

            # I want to send an image (generated by WolframAlpha), not embed a link (image would be regenerated if user clicked it + it would contain app_id)
            # And because discord.File has to open the file, I first save the file, then embed it, then delete it...
            # And to avoid overwriting during simultaneous calls, use the query's hash as the filename
            filename = "tmp" + str(hash(query))
            open(filename, "wb").write(response.content)
            
            await ctx.send(file=discord.File(filename, filename="result.png"))

            os.remove(filename)
                    
class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
                
    @commands.command(name='ping', help="Display bot's ping.")
    async def ping(self, ctx):
        ms = (datetime.datetime.utcnow() - ctx.message.created_at).total_seconds() * 1000
        await ctx.send(basic_emoji.get('Pepega') + ' 🏓 Pong! `{0}ms`'.format(int(ms)))

    @commands.command(name='deth', aliases=['death'], help="Find out when you or someone else will die.")
    async def deth(self, ctx, user: Union[discord.User, str, None]):
        # Set seed (consistent time everytime for each user)
        if not user:
            random.seed(ctx.message.author.id)
            name = "You"
        elif isinstance(user, discord.User):
            random.seed(user.id)
            name = user.display_name
        elif isinstance(user, discord.ClientUser):
            random.seed(user.id)
            name = user.name
        else:
            random.seed(abs(hash(user.lower())))
            name = user

        causes = [
            "cardiovascular disease",
            "cancer",
            "dementia",
            "diarrheal disease",
            "tuberculosis",
            "malnutrition",
            "HIV/AIDS",
            "malaria",
            "smoking",
            "suicide",
            "homicide",
            "natural disaster",
            "road incident",
            "drowning",
            "fire",
            "terrorism",
            "death by animal",
            "death by poison",
            "death by pufferfish",
            "death by sauna",
            "death by electrocution",
            "crushed by murphy bed"
        ]

        date = random_date(datetime.date(2025,1,1), datetime.date(2100, 1, 1))
        await ctx.send("{0} will die on {1}. Cause of deth: {2}.".format(name, custom_strftime('%B {S}, %Y', date), random.choice(causes)))
        # Use system time again (stops predictability of other things that use randomness)
        random.seed()

    @commands.command(name='fact', help="Get random fact about a day.")
    async def fact(self, ctx, arg1: str = '', arg2: str = ''):
        date = None
        msg = ''
        if not arg1 or not arg2:
            date = datetime.datetime.today()
            msg = 'On this day in the year '
        elif not arg1.isnumeric() or not arg2.isnumeric():
            await ctx.send("That's not even a numeric date. Try 'Month Day'.")
            await ctx.message.add_reaction(basic_emoji.get('Si'))
            return
        else:
            a1 = int(arg1)
            a2 = int(arg2)
            correctDate = None
            now = datetime.date.today()
            try:
                date = datetime.date(2000,a1,a2)
                msg = 'On ' + custom_strftime('%B {S}', date) + ' in the year '
                correctDate = True
            except ValueError:
                correctDate = False
            if not correctDate:
                await ctx.send("No..? You must be using the wrong calendar. Try 'Month Day'.")
                await ctx.message.add_reaction(basic_emoji.get('Si'))
                return

        facts = None
        status = await ctx.send('Looking up an interesting fact...')
        fact = ''
        wiki_success = True
        try:
            fact = wikipedia.page(date.strftime('%B') + ' ' + str(date.day)).section('Events')
            await status.edit(content='Searching wikipedia.com/wiki/' + date.strftime('%B') + '_' + str(date.day) + ' for an interesting fact.')
            facts = fact.splitlines()
        except:
            wiki_success = False
        if not wiki_success:
            await status.delete()
            fact = await ctx.send("Couldn't access wikipedia entry " + basic_emoji.get('Sadge'))
        elif not facts:
            await status.delete()
            fact = await ctx.send("Didn't find any interesting fact on wikipedia.com/wiki/" + date.strftime('%B') + '_' + str(date.day) + ". Probably retarded formatting on this page for the 'events' section." + sad_emoji )
        else:
            await status.delete()
            fact = await ctx.send(msg + random.choice(facts))
            await fact.add_reaction(random.choice(scoots_emoji))

    @commands.command(name='roll', help='Generate a random number between 1 and 100 by default.')
    async def roll(self, ctx, input: str = '100'):
        result = "No, I don't think so. " + basic_emoji.get('forsenSmug')
        if input.isnumeric():
            result = str(random.randint(1, int(input)))
        else:
            await ctx.message.add_reaction(basic_emoji.get('Si'))
        await ctx.send(result)

    @commands.command(name='decide', aliases=['choose'], help="Decide between options.")
    async def decide(self, ctx, *args):
        # No arguments -> exit
        if not args:
            await ctx.send("Decide between what? " + basic_emoji.get('Pepega') + basic_emoji.get('Clap') + "\nUse `;`, `:`, `,` or ` or `, to separate options.")
            await ctx.message.add_reaction(basic_emoji.get('Si'))
            return

        raw = ' '.join(str(i) for i in args)

        options = raw.split(';')
        if len(options) < 2:
            options = raw.split(':')
            if len(options) < 2:
                options = raw.split(',')
                if len(options) < 2:
                    options = raw.split(' or ')

        if len(options) < 2:
            await ctx.send("Separator not recognized, use `;`, `:`, `,` or ` or `, to separate options.")
        else:
            await ctx.send(random.choice(options))

    @commands.command(name='joke', aliases=['cringe'], help="Get a random joke")
    async def joke(self, ctx):
        id = random.randint(1, 3773)
        url_base = "http://stupidstuff.org/jokes/joke.htm?jokeid={0}".format(id)
        
        joke_source = None
        try:
            joke_source = requests.get(url_base, headers)
            joke_source.raise_for_status()
        except:
            fail = await ctx.send("Bad response (status code {0}) from {1}".format(joke_source.status_code, url_base))
            await fail.add_reaction(basic_emoji.get("Si"))
            return
        
        soup = BeautifulSoup(joke_source.content, 'html.parser')
        # joke_body = [item.get_text() for item in soup.select('span.gen_joke')]
        # joke_body = soup.find_all(class_='gen_joke')
        # joke_body = soup.find_all(class_=' gen_joke')
        # joke_body = soup.find_all('span', attrs={'class': 'gen_joke'})
        
        table = soup.find('table', attrs={'class': 'scroll'})
        
        if not table:
            fail = await ctx.send("Joke not found on {0}".format(url_base))
            await fail.add_reaction(basic_emoji.get("Si"))
            return
        
        for row in table.findAll("tr"):
            await ctx.send(row.text)
               
    @commands.command(name='chan', aliases=['4chan'], help="Get a random 4chan/4channel post.")
    async def chan(self, ctx, board: str = '', arg: str = ''):
        if board.lower() == "random":
            board_list = ['a','b','c','d','e','f','g','gif','d','h','hr','k','m','o','p','r','s','t','u','v','vg','w','wg','i','ic','r9k','cm','hm','y','3','adv','an','cgl','ck','co','diy','fa','fit','hc','int','jp','lit','mlp','mu','n','po','pol','sci','soc','sp','tg','toy','trv','tv','vp','wsg','x']
            board = random.choice(board_list)
        
        if not board:
            msg = await ctx.send("No board specified.")
            await msg.add_reaction(basic_emoji.get("Si"))
            return

        threads = None
        try:
            b = basc_py4chan.Board(board)
            threads = b.get_all_threads()
        except:
            msg = await ctx.send("`/{0}/` doesn't exist.".format(board))
            await msg.add_reaction(basic_emoji.get("Si"))
            return

        result = ""
        post = None
        # Find post with text
        if arg.lower() == "text" or arg.lower() == "txt":
            while not post or not post.text_comment:
                thread = random.choice(threads)
                post = random.choice(thread.posts)
                result = post.text_comment
        # Find post with image
        elif arg.lower() == "image" or arg.lower() == "img":
            while not post or not post.has_file:
                thread = random.choice(threads)
                post = random.choice(thread.posts)
                result = "|| {0} ||\n{1}".format(post.file_url, post.text_comment)
        else:
            while not post or not post.text_comment:
                thread = random.choice(threads)
                post = random.choice(thread.posts)
                if post.has_file:
                    result = "|| {0} ||\n{1}".format(post.file_url, post.text_comment)
                else:
                    result = post.text_comment
        
        await ctx.send(result[:2000])
        
class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_message(self, msg):
        if "p." not in msg.content and random.randint(0,100) <= 4:
            await msg.add_reaction(basic_emoji.get("Si"))
    
bot.add_cog(Garfield(bot))
bot.add_cog(Music(bot))
bot.add_cog(Utility(bot))
bot.add_cog(Miscellaneous(bot))
bot.add_cog(Test(bot))
bot.run(DISCORD_TOKEN)
