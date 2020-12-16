import datetime
import random


def random_date(start: datetime.datetime, end: datetime.datetime) -> datetime:
    """Get random datetime from interval

    start -- start of interval
    end -- end of interval
    """

    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds

    # Choose random second from interval
    random_second = random.randrange(int_delta)

    # Return new datetime in interval
    return start + datetime.timedelta(seconds=random_second)


def format_date(date: datetime.datetime) -> str:
    """Format datetime to string

    Example:
        1970.1.1 -> 1970/01/01
    """

    return "{0}/{1}/{2}".format(str(date.year), str(date.month).zfill(2), str(date.day).zfill(2))


def suffix(n: int) -> str:
    """Return number's suffix

    Example:
        1 -> "st"
        42 -> "nd"
        333 -> "rd"
    """
    return "th" if 11 <= n <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def custom_strftime(formatting: str, date: datetime.datetime) -> str:
    """Custom strftime formatting function, using fancy number suffixes (1st, 2nd, 3rd...)"""
    return date.strftime(formatting).replace("{S}", str(date.day) + suffix(date.day))
