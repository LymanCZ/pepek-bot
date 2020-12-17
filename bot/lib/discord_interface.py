import asyncio

import discord


async def add_choices_message(message: discord.Message, num: int, cancellable: bool = False) -> list:
    """React with choice emotes to message, return them as list"""

    # Only supports 10 max. stock "keycap digit" emojis
    assert 0 <= num <= 10

    # Indexed from 1 (more user friendly I think)
    number_emotes = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "0️⃣"]

    # Copy first n elements
    choices = number_emotes[:num]

    if cancellable:
        choices.append("❌")

    # Add them to message
    for emote in choices:
        await message.add_reaction(emote)

    return choices


async def wait_for_choice(bot: discord.ext.commands.Bot, user: discord.User, message: discord.Message, choices: list) -> int:
    """Wait for user to react with emote

    Example:
        No reaction (timeout) -> -1
        Cancelled (❌) -> 0
        Valid reaction -> 1 / 2 / 3 / ... (index of emoji in choices list + 1)
    """

    # Checks if added reaction is the one we're waiting for
    def check(reaction, author):
        if reaction.message.id == message.id and author.id == user.id:
            return author == user and (str(reaction.emoji) in choices)

    # Watch for reaction
    try:
        result, _ = await bot.wait_for("reaction_add", timeout=120, check=check)

    # No reaction after timeout
    except asyncio.TimeoutError:
        return -1

    if str(result.emoji) == "❌":
        return 0

    else:
        return choices.index(str(result.emoji)) + 1
