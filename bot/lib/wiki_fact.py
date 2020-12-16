import datetime
import random

import wikipedia

from lib.emotes import basic_emoji


class WikipediaError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


def get_day_fact(date: datetime.datetime) -> str:
    # Try to find an interesting fact
    try:
        raw = wikipedia.page(date.strftime("%B") + " " + str(date.day)).section("Events")
        # Library returns long string or None
        facts = raw.splitlines()

    # Returned None -> error -> stop
    except AttributeError:
        raise WikipediaError("No facts found on wikipedia.com/wiki/" + date.strftime("%B") + "_" + str(date.day) + " " + basic_emoji.get("Pepega"))

    # Returned empty string
    if not facts:
        raise WikipediaError("No facts found on wikipedia.com/wiki/" + date.strftime("%B") + "_" + str(date.day) + " " + basic_emoji.get("Pepega"))

    # Choose a random line (each line is 1 fact)
    else:
        return random.choice(facts)
