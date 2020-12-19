import asyncio

import discord
import youtube_dl

from lib.config import ytdl_format_options, ffmpeg_options


youtube_dl.utils.bug_reports_message = lambda: ""
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class Player(discord.PCMVolumeTransformer):
    """Audio player for Discord"""

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data
        self.ytdlData = data

        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    def revive(cls, player):
        """Revives player (essentially rewinds audio file to beginning)"""

        filename = player.ytdlData["url"]
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=player.ytdlData)

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        """Downloads audio from Youtube and returns player"""

        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if "entries" in data:
            # Take first item from a playlist
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Session:
    """Class representing listening session (tied to guild)"""

    _guild = None
    _ytdlData = None

    vc = None
    song_queue = []
    song = ""
    repeat = False

    def __init__(self, guild: discord.Guild):
        self._guild = guild

    def id(self) -> int:
        return self._guild.id

    def reset(self) -> None:
        """Restart session (clearing all variables)"""
        self.vc = None
        self.song_queue = []
        self.song = ""
        self.repeat = False

    def forceplay(self, song: str) -> None:
        """Add song to the front of queue"""

        self.song_queue.insert(0, song)

    def queue_empty(self) -> bool:
        return len(self.song_queue) == 0

    def queue_to_string(self) -> str:
        """Return queued songs as a long string"""

        if self.queue_empty():
            return "Queue is empty."

        queue = "🎶 Queue 🎶: "
        for queued_song in self.song_queue:
            queue += queued_song + "\n"

        return queue

    def next_song(self) -> bool:
        """Returns False if nothing is playing, True otherwise"""

        try:
            self.vc.stop()
            self.song = ""
            self.repeat = False

        except AttributeError:
            return False

        return True

    def pause(self) -> bool:
        """Returns False if nothing is playing, True otherwise"""

        try:
            self.vc.pause()

        except AttributeError:
            return False

        return True

    def stop(self) -> bool:
        """Return False if nothing is playing, True otherwise"""

        try:
            self.vc.stop()
            self.song_queue = []
            self.song = ""
            self.repeat = False

        except AttributeError:
            return False

        return True

    def is_paused(self) -> bool:
        """Returns True if connected and paused, False otherwise"""

        return self.vc is not None and self.vc.is_paused()

    def resume(self) -> None:
        """Resume playback"""

        self.vc.resume()

    async def connect(self, channel: discord.VoiceChannel) -> None:
        """Connect or move to voice channel"""

        # If not connected to voice channel
        if self.vc is None:
            self.vc = await channel.connect()

        # If connected to one, move to user's channel (can match current -> does nothing)
        else:
            await self.vc.move_to(channel)
