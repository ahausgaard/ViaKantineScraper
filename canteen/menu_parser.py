from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Calibration — fill these in after running:  python test_ocr.py "<image_url>"
# ---------------------------------------------------------------------------

# Lines with a Y centre AT OR BELOW this value are header rows (day names,
# title, etc.) and will be excluded from dish output.
# Set to the Y centre of the day-name row + a small buffer.
HEADER_Y_MAX: float | None = None   # e.g. 85.0   ← set after calibration

# (day_name, x_centre_of_column) — ordered Monday → Friday.
# Set the x values to the measured X centres of the day-name row.
DAY_COLUMNS: list[tuple[str, float]] = [
    ("Mandag",   0.0),   # ← replace 0.0 with measured X
    ("Tirsdag",  0.0),
    ("Onsdag",   0.0),
    ("Torsdag",  0.0),
    ("Fredag",   0.0),
]

# Lines further than this many pixels from the nearest column centre are
# treated as banners / footers and discarded.
MAX_X_DISTANCE: float = 200.0

# Consecutive lines within the same column are merged into one dish when
# their Y gap is SMALLER than this value.  Lines with a larger gap start
# a new dish.  Set to a value midway between the measured within-dish gap
# and the between-dish gap.
DISH_LINE_GAP: float = 40.0          # ← tune after calibration

# ---------------------------------------------------------------------------


def parse_week_number(text: str) -> str | None:
    """Return the week number string if text looks like a canteen menu, else None.
    Expects lowercase input.
    """
    if "menu" not in text or "uge" not in text:
        return None
    match = re.search(r"uge\s*(\d+)", text)
    return match.group(1) if match else None


def parse_daily_menus(lines: list[dict]) -> dict[str, list[str]]:
    """Parse OCR lines (from extract_lines_with_coords) into per-day dish lists.

    Algorithm:
    1. Drop header rows (y <= HEADER_Y_MAX) and far-from-column outliers.
    2. Assign each remaining line to the nearest DAY_COLUMNS X anchor.
    3. Within each column, sort by Y and merge consecutive lines whose Y gap
       is less than DISH_LINE_GAP into a single dish string (e.g. a wrapped
       long name). A gap >= DISH_LINE_GAP starts a new dish.

    Returns:
        {"Mandag": ["dish1", "dish2", ...], "Tirsdag": [...], ...}

    Note: Run test_ocr.py on a real menu image first, then update the
    calibration constants at the top of this module.
    """
    if HEADER_Y_MAX is None:
        raise RuntimeError(
            "HEADER_Y_MAX is not set. Run test_ocr.py on a real menu image "
            "and fill in the calibration constants in menu_parser.py."
        )

    # --- 1. Filter header rows and outliers ---
    dish_lines: list[dict] = []
    for line in lines:
        if line["y"] <= HEADER_Y_MAX:
            continue  # header row

        # Find nearest column
        nearest_day, nearest_x = min(DAY_COLUMNS, key=lambda col: abs(col[1] - line["x"]))
        if abs(nearest_x - line["x"]) > MAX_X_DISTANCE:
            continue  # banner / footer spanning the full width

        dish_lines.append({**line, "_day": nearest_day})

    # --- 2. Group by day, sort each group by Y ---
    buckets: dict[str, list[dict]] = {day: [] for day, _ in DAY_COLUMNS}
    for line in dish_lines:
        buckets[line["_day"]].append(line)

    for day in buckets:
        buckets[day].sort(key=lambda l: l["y"])

    # --- 3. Merge wrapped lines into dishes using Y-gap threshold ---
    result: dict[str, list[str]] = {}
    for day, col_lines in buckets.items():
        dishes: list[str] = []
        if not col_lines:
            result[day] = dishes
            continue

        current_parts = [col_lines[0]["text"]]
        for prev, curr in zip(col_lines, col_lines[1:]):
            gap = curr["y"] - prev["y"]
            if gap < DISH_LINE_GAP:
                # Same dish — continuation line
                current_parts.append(curr["text"])
            else:
                # New dish
                dishes.append(" ".join(current_parts))
                current_parts = [curr["text"]]

        dishes.append(" ".join(current_parts))  # flush last dish
        result[day] = dishes

    return result

