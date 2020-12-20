from multiprocessing import Process, Queue
from typing import Union

import discord
from discord.ext import commands

from lib.connectX import Board
from lib.discord_interface import add_choices_message, wait_for_choice, remove_choices
from lib.emotes import basic_emoji
from lib.player import Player


class Games(commands.Cog):
    """Various fun games"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="connect4", aliases=["connect", "connectX"], help="Play a game of Connect 4")
    async def connect4(self, ctx, user: Union[discord.User, None]):
        """Connect 4 against another human or AI"""

        # Parsing input
        # Tagging the bot itself creates ClientUser class
        if isinstance(user, discord.ClientUser):
            if user == self.bot.user:
                ai = True

        # Tagging anyone else creates User class
        elif isinstance(user, discord.User):
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

        # Game setup
        yellow = "🟡"
        red = "🔴"
        empty = "⬛"
        board = Board(7, 6, 4)
        player = Player(player1=ctx.message.author, player2=user, ai=ai)
        player.shuffle()

        # Message containing game
        board_msg = await ctx.send(board.to_string(yellow, red, empty) + "{0} on turn".format(player))

        # Add numbers on first turn
        reacts_added = False

        while not board.game_over():
            # If it's AI's turn
            if player.on_turn() == 2 and ai:
                # Update displayed board
                await board_msg.edit(content=board.to_string(yellow, red, empty) + basic_emoji.get("docSpin") + " {0} on turn".format(player))

                # Run AI as new process (CPU heavy)
                queue = Queue()
                p = Process(target=board.get_ai_move_mp, args=(queue, 7))
                p.start()
                p.join()

                column = queue.get()

            # If it's human's turn
            else:
                # Update displayed board
                await board_msg.edit(content=board.to_string(yellow, red, empty) + "{0} on turn".format(player))

                # Add numbers if not already present
                if not reacts_added:
                    reacts_added = True
                    try:
                        await board_msg.clear_reactions()
                    except discord.HTTPException:
                        pass
                    except discord.Forbidden:
                        await ctx.send("I am missing permission to manage messages (cannot remove reactions) " + basic_emoji.get("forsenT"))
                    columns = await add_choices_message(board_msg, 7)

                # Wait for human to choose a column
                column = await wait_for_choice(self.bot, player.get_user_on_turn(), board_msg, columns) - 1

                # No column chosen
                if column < 0:
                    await board_msg.edit(content=board.to_string(yellow, red, empty) + "{0} timed out".format(player))
                    await remove_choices(board_msg)
                    return

            # Drop piece down the selected column
            board.drop_piece(column, player.on_turn())

            # If it filled up the column, invalidate that column (can't be played again)
            if not board.column_not_full(column):
                columns[column] = "placeholder"

            player.next()

        # Game ended -> display result
        if board.winner is not None:
            await board_msg.edit(content=board.to_string(yellow, red, empty) + "{0} won!".format(player[board.winner]))
        else:
            await board_msg.edit(content=board.to_string(yellow, red, empty) + "It's a draw!")

        await remove_choices(board_msg)


def setup(bot):
    bot.add_cog(Games(bot))
