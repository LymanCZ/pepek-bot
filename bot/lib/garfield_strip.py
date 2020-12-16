import datetime

import requests
from bs4 import BeautifulSoup

from lib.config import headers
from lib.datetime_lib import format_date


class GarfieldError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


def valid_date(date: datetime.datetime) -> int:
    """Checks if a Garfield strip came out on a specified date"""
    if date > datetime.datetime.today():
        return 1
    if date < datetime.datetime(1978, 6, 19):
        return -1
    return 0


def garfield_strip(date: datetime.datetime) -> str:
    """Return link to Garfield comic strip for a given date"""

    # Check date
    if valid_date(date) > 0:
        raise GarfieldError("You will have to wait for that day to come.")
    elif valid_date(date) < 0:
        raise GarfieldError("Unfortunately, Garfield didn't exist before 19th June 1978.")

    # Construct URL using date
    url = "http://www.gocomics.com/garfield/" + format_date(date)

    try:
        response = requests.get(url, headers)
        response.raise_for_status()

    except requests.HTTPError:
        raise GarfieldError("Bad response (status code {0}) from {1})".format(response.status_code, url))

    # Scrape page for comic
    soup = BeautifulSoup(response.content, "html.parser")
    picture = soup.find_all("picture", attrs={"class": "item-comic-image"})

    # If strip missing
    if not picture or not picture[0]:
        raise GarfieldError("Garfield comic not found on " + url)

    # Else return comic strip
    return picture[0].img["src"]
