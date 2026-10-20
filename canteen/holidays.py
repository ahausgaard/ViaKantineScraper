from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable


@dataclass(frozen=True)
class Holiday:
    """A recurring period where the canteen is closed.

    During an active holiday we skip scraping. On /menu, if ``image_filename``
    is set we show that image (a file in canteen/images/) instead of a menu;
    otherwise we show a text-only "closed" message.

    ``start_week`` and ``end_week`` are ISO week numbers, inclusive, and recur
    every year — no need to update them annually. A range whose start week is
    later in the year than its end week wraps across new year (e.g. Christmas:
    start_week=52, end_week=1). Leave ``end_week`` out for a one-week holiday.

    For holidays that move each year (e.g. Easter), pass a function that takes
    the ISO year and returns the week number instead of a fixed int.
    """

    name: str  # human-readable, shown in Slack
    start_week: int | Callable[[int], int]  # ISO week number, inclusive
    end_week: int | Callable[[int], int] | None = None  # ISO week number, inclusive; None means a single week
    image_filename: str | None = None  # optional file in canteen/images/ shown instead of a menu
    emoji: str = "🌴"


def easter_sunday(year: int) -> date:
    """Easter Sunday in the Gregorian calendar (anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def easter_week(year: int) -> int:
    """ISO week starting the Monday after Palm Sunday (the week Easter Sunday ends)."""
    return easter_sunday(year).isocalendar()[1]


# Add new entries here to reuse the same behaviour for other holidays.
HOLIDAYS: list[Holiday] = [
    Holiday(
        name="Summer holiday",
        image_filename="summerRye.jpg",
        start_week=27,
        end_week=31,
        emoji="🌴"
    ),
    Holiday(
        name="Autumn Break",
        image_filename="autumnRye.jpg",
        start_week=42,
        emoji="🍂"
    ),
    Holiday(
        name="Easter Break",
        image_filename="easterRye.jpg",
        start_week=easter_week,  # the week after Palm Sunday, recomputed every year
        emoji="🐣"
    ),
    Holiday(
        name="Christmas Break",
        image_filename="christmasRye.jpg",
        start_week=52,
        end_week=52,
        emoji="🎅"
    ),
    Holiday(
        name="Winter Break",
        image_filename="winterRye.jpg",
        start_week=7,
        emoji="❄️"
    ),
]


def _in_range(week: int, start_week: int, end_week: int | None) -> bool:
    if end_week is None:
        end_week = start_week
    if start_week <= end_week:
        return start_week <= week <= end_week
    # Range wraps across the new year (e.g. Christmas).
    return week >= start_week or week <= end_week


def _resolve(week: int | Callable[[int], int] | None, year: int) -> int | None:
    return week(year) if callable(week) else week


def active_holiday(today: date | None = None) -> Holiday | None:
    """Return the holiday active on ``today`` (defaults to today), or None."""
    if today is None:
        today = date.today()
    year, week, _ = today.isocalendar()
    for holiday in HOLIDAYS:
        start_week = _resolve(holiday.start_week, year)
        end_week = _resolve(holiday.end_week, year)
        if _in_range(week, start_week, end_week):
            return holiday
    return None
