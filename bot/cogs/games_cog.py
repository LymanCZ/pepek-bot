import asyncio
import json
import random
import re
import requests
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

    @commands.command(name="connect1", aliases=["connec1", "connec"], help="Play a game of Connect 1")
    async def connect1(self, ctx, arg1: Union[discord.user.User, str, None], arg2: Union[discord.user.User, str, None]):
        """Connect 1 against another human or AI"""

        await self.connect_x(ctx, width=1, height=1, pieces=1, depth=25, arg1=arg1, arg2=arg2)

    @commands.command(name="connect2", help="Play a game of Connect 2")
    async def connect2(self, ctx, arg1: Union[discord.user.User, str, None], arg2: Union[discord.user.User, str, None]):
        """Connect 2 against another human or AI"""

        await self.connect_x(ctx, width=2, height=3, pieces=2, depth=25, arg1=arg1, arg2=arg2)

    @commands.command(name="connect3", help="Play a game of Connect 3")
    async def connect3(self, ctx, arg1: Union[discord.user.User, str, None], arg2: Union[discord.user.User, str, None]):
        """Connect 3 against another human or AI"""

        await self.connect_x(ctx, width=5, height=4, pieces=3, depth=25, arg1=arg1, arg2=arg2)

    @commands.command(name="connect4", aliases=["connect", "connectX"], help="Play a game of Connect 4")
    async def connect4(self, ctx, arg1: Union[discord.user.User, str, None], arg2: Union[discord.user.User, str, None]):
        """Connect 4 against another human or AI"""

        await self.connect_x(ctx, width=7, height=6, pieces=4, depth=6, arg1=arg1, arg2=arg2)

    @commands.command(name="connect5", help="Play a game of Connect 5")
    async def connect5(self, ctx, arg1: Union[discord.user.User, str, None], arg2: Union[discord.user.User, str, None]):
        """Connect 5 against another human or AI"""

        await self.connect_x(ctx, width=10, height=9, pieces=5, depth=5, arg1=arg1, arg2=arg2)

    async def connect_x(self, ctx, width: int, height: int, pieces: int, depth: int, arg1: Union[discord.user.User, str, None], arg2: Union[discord.user.User, str, None]):
        """ConnectX of variable size"""

        # Parsing input
        if isinstance(arg1, str):
            user = arg2
            emote = arg1
        else:
            user = arg1
            emote = arg2

        # Tagging a user creates User (or Member) class
        if isinstance(user, discord.user.User) or isinstance(user, discord.member.Member):
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
        if isinstance(user, discord.user.ClientUser) and isinstance(emote, discord.user.ClientUser):
            bvb = True

        elif isinstance(emote, str) and len(emote) != 0:
            await self.set_icon(ctx, emote)

        # Game setup
        board = ConnectX(width, height, pieces)
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
                p = Process(target=board.get_ai_move_mp, args=(queue, 1, player.on_turn(), depth))
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
                    columns = await add_choices_message(board_msg, width, cancellable=True)

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
        
    @commands.command(name="quiz", aliases=["trivia"], help="I heard that you like Trivia Quiz...")
    @commands.cooldown(1,30,commands.BucketType.user)
    async def quiz(self, ctx, arg: int = 1):
        """Trivia quiz"""
        
        if arg > 10:
            toomuch = await ctx.send("**What the hell? Way too many questions. Actually - 10 questions should be enough.**")
            await asyncio.sleep(3)
            await toomuch.delete()
            arg = 10
        
        if arg < 1:
            impossible_arg = await ctx.send("Not possible, how about 3 questions instead?")
            await asyncio.sleep(3)
            await impossible_arg.delete()
            arg = 3
        
        i = 0
        score = 0
        timeout_count = 0

        """Quiz cycle -> scrape next question and answers"""
        while i < arg:
            quiz = requests.get("https://opentdb.com/api.php?amount=1&type=multiple").json()
            question = (quiz["results"][0]["question"])
            question = question.replace("&quot;", "\"")
            question = question.replace("&#039;", "\'")
            question_msg = await ctx.send("**" + question + "**")
            correct = (quiz["results"][0]["correct_answer"])
            correct = correct.replace("&quot;", "\"")
            correct = correct.replace("&#039;", "\'")
            quiz_list = (quiz["results"][0]["incorrect_answers"])
            quiz_list.append(correct)
            random.shuffle(quiz_list)
            quiz_list = [w.replace("&quot;", "\"") for w in quiz_list]
            quiz_list = [w.replace("&#039;", "\'") for w in quiz_list]
            corr_index = quiz_list.index(correct)
            
            """Figure out which one is correct and compare with user's reaction"""
            if corr_index == 0:
                answer = "🇦"
            elif corr_index == 1:
                answer = "🇧"
            elif corr_index == 2:
                answer = "🇨"
            else:
                answer = "🇩"
                
            """Add reactions forsenJoy"""
            for x, word in enumerate(quiz_list):
                if word == "&quot;":
                    quiz_list[x] = "\""
            for x, word in enumerate(quiz_list):
                if word == "&#039;":
                    quiz_list[x] = "\'"
            for x, word in enumerate(quiz_list):
                if word == "&amp;":
                    quiz_list[x] = "&"
            answer_msg = await ctx.send(" | ".join(quiz_list))
            await answer_msg.add_reaction("🇦")
            await answer_msg.add_reaction("🇧")
            await answer_msg.add_reaction("🇨")
            await answer_msg.add_reaction("🇩")
            
            """Waiting for the user's reaction residentSleeper"""
            def check(reaction, user):
                return str(reaction.emoji) and user == ctx.author

            """Based on the reaction"""
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=25, check=check)
                if str(reaction.emoji) == answer:
                    status_corr = await ctx.send("Yes, ** " + correct + " **is correct.")
                    await status_corr.add_reaction("👍")
                    await asyncio.sleep(3)
                    await status_corr.delete()
                    score = score + 1
                if str(reaction.emoji) != answer:
                    status_icon = await ctx.send("No, I don't think so. **" + correct + " **is the right answer.")
                    await status_icon.add_reaction(basic_emoji.get("Sadge"))
                    await asyncio.sleep(5)
                    await status_icon.delete()
            except asyncio.TimeoutError:
                to = await ctx.send("You ran out of time!")
                await to.add_reaction(basic_emoji.get("Pepega"))
                await asyncio.sleep(3)
                await to.delete()
                timeout_count += 1
                
            """Delete the question and repeat the cycle"""
            i += 1
            await question_msg.delete()
            await answer_msg.delete()
            
            """User AFK"""
            if timeout_count == arg and arg > 1:
                afk = await ctx.send("Timed out.")
                await afk.add_reaction(basic_emoji.get("Si"))
                return
            
            """Conclusion"""
            if i == arg and arg > 1:
                count = score / arg
                if count > 0.7:
                    conclusion_list = ["That's a lot of knowledge.", "Smart one, are not you?", "PhDr. Milan Beneš would be proud.", "Well met!", "Never doubt the god gamer!", "That was pretty good.", "EZ4ANTS"]
                    conclusion = random.choice(conclusion_list)
                elif count > 0.5:
                    conclusion_list = ["Not Great, Not Terrible", "That was... pretty average, I guess?", "Nice try nonetheless.", "Enough points to pass my exam."]
                    conclusion = random.choice(conclusion_list)
                elif count > 0.3:
                    conclusion_list = ["I can tell that this is not your lucky day, is it?", "Never lucky man ...", "Better luck next time!", "Pretty underwhelming."]
                    conclusion = random.choice(conclusion_list)
                elif count > 0.1:
                    conclusion_list = ["MAN VA FAN.", "Terrible...", "Blame it on the black star.", "Just unlucky, right?", "Next time, you should try harder."]
                    conclusion = random.choice(conclusion_list)
                else:
                    conclusion_list = ["You are trolling, right?", "Apparently you have got more chromosomes than I thought.", "Is this some kind of twisted joke?", "A total waste of time.", "ZULOL"]
                    conclusion = random.choice(conclusion_list)
                await ctx.send("**You have answered " + str(score) + " out of " + str(arg) + " questions correctly. " + conclusion + "**")
    
    @client.command(name="hangman", aliases=["hm"], help="Hangman: The Videogame")
    @commands.cooldown(1,30,commands.BucketType.user)
    async def nig(self,ctx):
        
        """Scrape random word"""
        source = requests.get("https://random-word-api.herokuapp.com/word?number=1").text
        soup = BeautifulSoup(source,"html.parser")
        word = str(soup)
        word = re.sub('[^a-zA-Z]+', '', word)

        """:painsge:"""
        word = word.replace("a", "🇦")
        word = word.replace("b", "🇧")
        word = word.replace("c", "🇨")
        word = word.replace("d", "🇩")
        word = word.replace("e", "🇪")
        word = word.replace("f", "🇫")
        word = word.replace("g", "🇬")
        word = word.replace("h", "🇭")
        word = word.replace("i", "🇮")
        word = word.replace("j", "🇯")
        word = word.replace("k", "🇰")
        word = word.replace("l", "🇱")
        word = word.replace("m", "🇲")
        word = word.replace("n", "🇳")
        word = word.replace("o", "🇴")
        word = word.replace("p", "🇵")
        word = word.replace("q", "🇶")
        word = word.replace("r", "🇷")
        word = word.replace("s", "🇸")
        word = word.replace("t", "🇹")
        word = word.replace("u", "🇺")
        word = word.replace("v", "🇻")
        word = word.replace("w", "🇼")
        word = word.replace("x", "🇽")
        word = word.replace("y", "🇾")
        word = word.replace("z", "🇿")

        original_word = word
        letter_no = (len(word))
        hidden_word = letter_no * "_"
        i = 0
        mistakes_no = 0
    
        """Hangman itself"""
        play_field = await ctx.send("_-_-_-_-_-_-_-_-_-_-_-_-\n|\n|\n|\n|\n|\n|")
        guessed_letters = await ctx.send(f"**React here ⬇️ This word has {letter_no} letters**")
        await guessed_letters.add_reaction("❌")
    
        """Various conditions"""
        while i < letter_no:
            def check(reaction, user):
                return str(reaction.emoji) and user == ctx.author
      
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60, check=check)
            
            """Forfeited"""
            if str (reaction.emoji) == "❌":
                ff = await ctx.send(f"Forfeited ... the word is: ```{original_word}```")
                await asyncio.sleep(5)
                await guessed_letters.delete()
                await play_field.delete()
                await ff.delete()
                return
            
            """Wrong letter"""
            if str(reaction.emoji) not in word:
                mistakes_no = mistakes_no + 1
                if mistakes_no == 1:
                    await play_field.edit(content="_-_-_-_-_-_-_-_-_-_-_-_-\n|            🧢\n| \n|\n|\n|\n|")
                if mistakes_no == 2:
                    await play_field.edit(content="_-_-_-_-_-_-_-_-_-_-_-_-\n|            🧢\n|            😟\n|\n|\n|\n|")
                if mistakes_no == 3:
                    await play_field.edit(content="_-_-_-_-_-_-_-_-_-_-_-_-\n|            🧢\n|            😟\n|            👕\n|\n|\n|")
                if mistakes_no == 4:
                    await play_field.edit(content="_-_-_-_-_-_-_-_-_-_-_-_-\n|            🧢\n|            😟\n|            👕\n|            🩳\n|\n|")
                if mistakes_no == 5:
                    await play_field.edit(content="_-_-_-_-_-_-_-_-_-_-_-_-\n|            🧢\n|            😟\n|            👕\n|            🩳\n|          👞👞\n|")
                    await guessed_letters.delete()
                    await ctx.send(f"Pepek Jr. died! The word is:``` {original_word}```")
                    return
            
            """Right letter"""
            if str(reaction.emoji) in word:
                count = word.count(reaction.emoji)
                letter_me = ([pos for pos, char in enumerate(original_word) if char ==   reaction.emoji])

                z=0
                while z < count:
                    letter_index = (letter_me[z])
                    hidden_word = hidden_word[:letter_index] + reaction.emoji + hidden_word[letter_index+1:]
                    z = z + 1

                word = word.replace(reaction.emoji,"")
                i = i+count
                await guessed_letters.edit(content ="```" + hidden_word + "```")
        
      except asyncio.TimeoutError:
        to = await ctx.send("You ran out of time!")
        await asyncio.sleep(3)
        await to.delete()
        await guessed_letters.delete()
        await play_field.delete()
        return
  
    await guessed_letters.delete()
    await ctx.send(f"You win - the word is: ```{original_word}```")            
                
                
def setup(bot):
    bot.add_cog(Games(bot))
