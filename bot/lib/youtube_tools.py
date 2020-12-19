import os

import discord
from googleapiclient.discovery import build

from lib.discord_interface import add_choices_message, wait_for_choice
from lib.emotes import basic_emoji


YOUTUBE_API_TOKEN = os.getenv("YOUTUBE_API_TOKEN")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_TOKEN)


def youtube_search(title: str) -> list:
    """Return top 5 results (videos only, no channels or playlists)"""

    assert not title.isspace()

    try:
        search_response = youtube.search().list(q=title, part="id,snippet", maxResults=10).execute()
    except:  # Google has awful documentation, it's impossible to find which exceptions a method can throw
        raise ConnectionError

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


async def select_video(bot: discord.ext.commands.Bot, ctx: discord.ext.commands.Context, query: str) -> str:
    """Extract Youtube URL, returns empty string if failed"""

    # If URL contained in argument
    if "youtube.com/watch?v=" in query or "youtu.be/" in query:
        # Assuming it's the first 'word' of argument
        return query.partition(" ")[0]

    # Else search youtube for video title
    else:
        try:
            videos = youtube_search(query)
        except ConnectionError:
            msg = await ctx.send(basic_emoji.get("hackerCD") + "HTTP error. " + basic_emoji.get("Sadge"))
            await msg.add_reaction(basic_emoji.get("Si"))
            return ""

        # 0 videos -> exit
        if len(videos) == 0:
            msg = await ctx.send("0 videos found. " + basic_emoji.get("Sadge"))
            await msg.add_reaction(basic_emoji.get("Si"))
            return ""

        # 1 video -> we have a winner
        elif len(videos) == 1:
            return "https://www.youtube.com/watch?v=" + videos[0][1]

        # Else let user to choose which one they meant
        else:
            # Only giving 5 choices max
            number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
            valid_numbers = []

            poll = ""
            i = 0

            # Iterate over all (5 at most) found videos, pair = ('title - channel' : 'video_id')
            for pair in videos:
                # Add title to message
                poll += number_emojis[i] + ". " + pair[0] + "\n"
                # Add valid option
                valid_numbers.append(number_emojis[i])
                i += 1

            # Display message with available videos
            msg = await ctx.send(poll)
            await add_choices_message(msg, len(valid_numbers), cancellable=True)

            # Wait for user to choose
            choice = await wait_for_choice(bot, ctx.author, msg, valid_numbers, cancellable=True)

            await msg.delete()

            # Cancelled or timed out
            if choice <= 0:
                return ""

            return "https://www.youtube.com/watch?v=" + videos[choice - 1][1]
