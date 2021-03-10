import os
import base64

import discord


# HTTP headers
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "3600",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0"
    # "Authorization": base64.b64encode(bytes("Basic username:password", "utf-8"))
}

# Log-in for youtube to download age-restricted videos ~this still doesn't solve the issue, I don't understand why~
YT_MAIL = os.getenv("YT_MAIL")
YT_PASS = os.getenv("YT_PASS")
# youtube-dl wants cookies as a text file ~this also doesn't solve the age-restriction issue~
with open("cookies.txt", "w") as text_file:
    print(os.getenv('COOKIE_DATA'), file=text_file)

ytdl_format_options = {
    "cookies": "cookies.txt",
    "user_agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0",
    "username": YT_MAIL,
    "password": YT_PASS,
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0"  # Bind to IPv4 since IPv6 addresses cause issues sometimes
}

# -vn discards video stream
ffmpeg_options = {
    "options": "-vn"
}

# Bot's discord activities
activities = [
    discord.Game(name="with křemík."),
    discord.Activity(type=discord.ActivityType.listening, name="frequencies."),
    discord.Activity(type=discord.ActivityType.watching, name="you.")
]

geckodriver_path = os.getenv("GECKODRIVER_PATH")
firefox_bin = os.getenv("FIREFOX_BIN")
