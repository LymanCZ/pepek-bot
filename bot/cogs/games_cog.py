import re
from multiprocessing import Process, Queue
from typing import Union

import discord
from discord.ext import commands

from lib.connectX import Board as ConnectX
from lib.discord_interface import add_choices_message, wait_for_choice, remove_choices
from lib.emoji import extract_emoji
from lib.emotes import basic_emoji
from lib.minesweeper import Minesweeper
from lib.player import Player


class Games(commands.Cog):
    """Various fun games"""
    def __init__(self, bot):
        self.bot = bot
        self.user_icon = {self.bot.user.id: "🔴"}

    def user_icons(self, user1: discord.User, user2: discord.User):
        """Return currently set user icons or default if not set"""

        if user1.id == user2.id:
            return "🟡", "🔴"

        if user1.id in self.user_icon:
            yellow = self.user_icon[user1.id]
        else:
            yellow = "🟡"

        if user2.id in self.user_icon:
            red = self.user_icon[user2.id]
        else:
            red = "🔴"

        return yellow, red

    @commands.command(name="icon", aliases=["set"], help="Set any emoji as your icon")
    async def set_icon(self, ctx, emote: str = ""):
        """Change user's icon to emoji"""

        if len(emote) == 0:
            await ctx.send("No emote specified")
            await ctx.message.add_reaction(basic_emoji.get("Si"))

        # Find every Discord emote
        discord_emotes = re.findall(r"<:\w*:\d*>", ctx.message.content)

        # Unicode emojis compatible by default
        compatible = extract_emoji(ctx.message.content)

        # Filter foreign emotes
        for e in discord_emotes:
            for known in self.bot.emojis:
                if e == str(known):
                    compatible.append(e)

        # Remove duplicates
        compatible = list(set(compatible))

        # If user specified compatible custom emoji
        if len(compatible) == 1:
            self.user_icon[ctx.author.id] = str(compatible[0])
            await ctx.message.add_reaction("✅")

        elif len(compatible) == 0:
            await ctx.send("I can't use that emote " + basic_emoji.get("Sadge"))

        else:
            await ctx.send("Too many emotes specified " + basic_emoji.get("Pepega"))

    @commands.command(name="connect4", aliases=["connect", "connectX"], help="Play a game of Connect 4")
    async def connect4(self, ctx, arg1: Union[discord.User, str, None], arg2: Union[discord.User, str, None]):
        """Connect 4 against another human or AI"""

        # Parsing input
        if isinstance(arg1, str):
            user = arg2
            emote = arg1
        else:
            user = arg1
            emote = arg2

        # Tagging a user creates User (or Member) class
        if isinstance(user, discord.User):
            # If user is a bot -> bot is unlikely to be able to play connect4
            if user.bot:
                await ctx.send("I don't think {0} would play with you ".format(user.mention) + basic_emoji.get("forsenSmug"))
                return

            # Tagged user is a human
            ai = False

            # User tagged themselves (permitted)
            if user == ctx.message.author:
                await ctx.message.add_reaction(basic_emoji.get("Pepega"))
                await ctx.message.add_reaction(basic_emoji.get("Clap"))

        # No tag provided -> play against AI
        else:
            ai = True
            user = self.bot.user

        # Bot vs Bot
        bvb = False
        if isinstance(user, discord.ClientUser) and isinstance(emote, discord.ClientUser):
            bvb = True

        elif isinstance(emote, str) and len(emote) != 0:
            await self.set_icon(ctx, emote)

        # Game setup
        board = ConnectX(7, 6, 4)
        columns = [None for _ in range(10)]
        player1 = ctx.message.author
        player2 = user
        if bvb:
            player1 = emote
        player = Player(player1=player1, player2=player2, ai=ai)
        player.shuffle()

        # Message containing game
        yellow, red = self.user_icons(player1, player2)
        board_msg = await ctx.send(board.to_string(yellow, red) + "{0} on turn".format(player))

        # Add numbers on first turn
        reacts_added = False

        while not board.game_over():
            # If it's AI's turn
            if player.on_turn() == 2 and ai or bvb:
                # Update displayed board
                yellow, red = self.user_icons(player1, player2)
                await board_msg.edit(content=board.to_string(yellow, red) + basic_emoji.get("docSpin") + " {0} on turn".format(player))

                # Run AI as new process (CPU heavy)
                queue = Queue()
                p = Process(target=board.get_ai_move_mp, args=(queue, 1, player.on_turn()))
                p.start()
                p.join()

                column = queue.get()

            # If it's human's turn
            else:
                # Update displayed board
                yellow, red = self.user_icons(player1, player2)
                await board_msg.edit(content=board.to_string(yellow, red) + "{0} on turn".format(player))

                # Add numbers if not already present
                if not reacts_added:
                    reacts_added = True
                    try:
                        await board_msg.clear_reactions()
                    except discord.Forbidden:
                        await ctx.send("I am missing permission to manage messages (cannot remove reactions) " + basic_emoji.get("forsenT"))
                    except discord.HTTPException:
                        pass
                    columns = await add_choices_message(board_msg, 7, cancellable=True)

                # Wait for human to choose a column
                column = await wait_for_choice(self.bot, player.get_user_on_turn(), board_msg, columns, cancellable=True) - 1

                # No column chosen or player forfeited
                if column < 0:
                    yellow, red = self.user_icons(player1, player2)
                    status = "forfeited" if column == -1 else "timed out"
                    await board_msg.edit(content=board.to_string(yellow, red) + "{0} {1}".format(player, status))
                    await remove_choices(board_msg)
                    return

            # Drop piece down the selected column
            board.drop_piece(column, player.on_turn())

            # If it filled up the column, invalidate that column (can't be played again)
            if not board.column_not_full(column):
                columns[column] = "placeholder"

            player.next()

        # Game ended -> display result
        yellow, red = self.user_icons(player1, player2)
        if board.winner is not None:
            await board_msg.edit(content=board.to_string(yellow, red) + "{0} won!".format(player[board.winner]))
        else:
            await board_msg.edit(content=board.to_string(yellow, red) + "It's a draw!")

        await remove_choices(board_msg)

    @commands.command(name="minesweeper", aliases=["mines"], help="Generate a minefield")
    async def minesweeper(self, ctx, bombs: int = 25):
        """Displays a minefield"""

        if bombs > 99:
            await ctx.send("That's too many bombs.")
            return
        elif bombs < 1:
            await ctx.send("That wouldn't be minesweeper, just floorsweeper.")
            return

        field = Minesweeper(width=10, height=10, bombs=bombs)

        await ctx.send(field.to_string(spoiler=True))


def setup(bot):
    bot.add_cog(Games(bot))
