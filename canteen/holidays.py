from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Holiday:
    """A recurring period where the canteen is closed.

    During an active holiday we skip scraping. On /menu, if ``image_filename``
    is set we show that image (a file in canteen/images/) instead of a menu;
    otherwise we show a text-only "closed" message.

    ``start_week`` and ``end_week`` are ISO week numbers, inclusive, and recur
    every year — no need to update them annually. A range whose start week is
    later in the year than its end week wraps across new year (e.g. Christmas:
    start_week=52, end_week=1).
    """

    name: str                          # human-readable, shown in Slack
    start_week: int                    # ISO week number, inclusive
    end_week: int                      # ISO week number, inclusive
    image_filename: str | None = None  # optional file in canteen/images/ shown instead of a menu
    emoji: str = "🌴"


# Add new entries here to reuse the same behaviour for other holidays.
HOLIDAYS: list[Holiday] = [
    Holiday(
        name="Summer holiday",
        image_filename="summerRye.jpg",
        start_week=27,
        end_week=31,
        emoji="🌴",
    ),
]


def _in_range(week: int, start_week: int, end_week: int) -> bool:
    if start_week <= end_week:
        return start_week <= week <= end_week
    # Range wraps across the new year (e.g. Christmas).
    return week >= start_week or week <= end_week


def active_holiday(today: date | None = None) -> Holiday | None:
    """Return the holiday active on ``today`` (defaults to today), or None."""
    if today is None:
        today = date.today()
    week = today.isocalendar()[1]
    for holiday in HOLIDAYS:
        if _in_range(week, holiday.start_week, holiday.end_week):
            return holiday
    return None
