import asyncio
from typing import Union

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


async def wait_for_choice(bot: discord.Client, user: Union[discord.User, discord.Member], message: discord.Message, choices: list, cancellable: bool = False) -> int:
    """Wait for user to react with emote, then remove their reaction

        Example:
            No reaction (timeout) -> -1
            Cancelled (❌) -> 0
            Valid reaction -> 1 / 2 / 3 / ... (index of emoji in choices list + 1)
        """

    number_emotes = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "0️⃣"]

    if cancellable:
        number_emotes.append("❌")
        choices.append("❌")

    # Checks if added reaction is the one we're waiting for
    def check(payload: discord.RawReactionActionEvent):
        if message.id == payload.message_id and payload.emoji.name in number_emotes and payload.user_id != bot.user.id:
            return True

    choice = None
    author_id = -1

    while choice not in choices or author_id != user.id:

        # Watch for reaction
        try:
            payload: discord.RawReactionActionEvent = await bot.wait_for("raw_reaction_add", timeout=300, check=check)
            choice = payload.emoji.name
            author_id = payload.user_id

        # No reaction after timeout
        except asyncio.TimeoutError:
            return -1

        # Remove user's reaction
        try:
            # Message.remove_reaction requires a Snowflake - according to documentation, it has 2 attributes, `id` and `created_at`
            # Well, Snowflake is missing the `id` attribute in discord.py 1.7.3, but remove_reaction still requires it
            snowflake = discord.abc.Snowflake
            snowflake.id = author_id
            await message.remove_reaction(payload.emoji.name, snowflake)
        except discord.errors.Forbidden:
            pass

    if choice == "❌":
        return 0
    else:
        # Return emote as the number it represents (1️⃣ represents 1, 0️⃣️ represents 10)
        return choices.index(choice) + 1


async def remove_choices(message: discord.Message) -> None:
    """Remove all number emotes from message"""

    number_emotes = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "0️⃣", "❌"]

    for emote in number_emotes:
        try:
            await message.clear_reaction(emote)
        except (discord.HTTPException, discord.Forbidden, discord.NotFound):
            pass
