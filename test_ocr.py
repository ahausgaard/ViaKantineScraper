"""OCR calibration & validation script.

Usage:
    python test_ocr.py "<image_url>"

What it does:
    1. Calls Azure Vision on the given image URL.
    2. Prints every detected line sorted by Y (top→bottom) with its X/Y
       coordinates — use this to fill in the calibration constants in
       canteen/menu_parser.py.
    3. If calibration constants are already set, also runs parse_daily_menus()
       and prints the structured day→dishes output so you can validate
       correctness.

Steps to calibrate:
    a) Run once and look at the RAW LINES output.
    b) Find the lines containing "Mandag", "Tirsdag", etc. — note their X and Y
       values.  The Y of that row + ~10 px buffer → HEADER_Y_MAX.
       The five X values → DAY_COLUMNS x_centres.
    c) Look at the Y gaps between lines in the same column:
         - Wrapped lines of the same dish will be close together (small gap).
         - Different dishes will have a larger gap.
       Pick DISH_LINE_GAP midway between those two gap sizes.
    d) Edit canteen/menu_parser.py and fill in HEADER_Y_MAX, DAY_COLUMNS,
       and (if needed) DISH_LINE_GAP.
    e) Re-run this script — the PARSED DAILY MENUS section will now show the
       structured result.
"""

import sys
from pathlib import Path

# Allow running from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).parent))

from canteen.ocr import extract_lines_with_coords
from canteen import menu_parser


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python test_ocr.py \"<image_url>\"")
        sys.exit(1)

    image_url = sys.argv[1]
    print(f"Running OCR on: {image_url}\n")

    lines = extract_lines_with_coords(image_url)
    if not lines:
        print("No lines extracted — check your VISION_ENDPOINT / VISION_KEY.")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # 1. Raw dump sorted by Y (top → bottom), then X (left → right)
    # -----------------------------------------------------------------------
    sorted_lines = sorted(lines, key=lambda l: (l["y"], l["x"]))

    print("=" * 70)
    print(f"{'RAW LINES':^70}")
    print("=" * 70)
    print(f"  {'X':>7}  {'Y':>7}   TEXT")
    print("-" * 70)
    for line in sorted_lines:
        print(f"  {line['x']:>7.1f}  {line['y']:>7.1f}   {line['text']}")

    print()
    print("Use the X values of the day-name row to set DAY_COLUMNS,")
    print("and the Y of that row + ~10 px buffer to set HEADER_Y_MAX")
    print("in canteen/menu_parser.py.\n")

    # -----------------------------------------------------------------------
    # 2. Y-gap analysis per apparent column cluster (helps tune DISH_LINE_GAP)
    # -----------------------------------------------------------------------
    # Show consecutive Y gaps for any lines that share a similar X bucket.
    # We just print all consecutive Y-gaps so the pattern is obvious.
    print("=" * 70)
    print(f"{'CONSECUTIVE Y GAPS (all lines, sorted by Y)':^70}")
    print("=" * 70)
    for prev, curr in zip(sorted_lines, sorted_lines[1:]):
        gap = curr["y"] - prev["y"]
        marker = " ← large gap (dish boundary?)" if gap > 20 else ""
        print(f"  gap={gap:>6.1f}px  |  '{prev['text']}' → '{curr['text']}'{marker}")

    # -----------------------------------------------------------------------
    # 3. Parsed output (only if calibration constants are set)
    # -----------------------------------------------------------------------
    print()
    if menu_parser.HEADER_Y_MAX is None or all(x == 0.0 for _, x in menu_parser.DAY_COLUMNS):
        print("=" * 70)
        print("PARSED DAILY MENUS: skipped — calibration constants not set yet.")
        print("Fill in HEADER_Y_MAX and DAY_COLUMNS in canteen/menu_parser.py,")
        print("then re-run this script.")
        print("=" * 70)
        return

    print("=" * 70)
    print(f"{'PARSED DAILY MENUS':^70}")
    print("=" * 70)
    try:
        daily = menu_parser.parse_daily_menus(lines)
        for day, dishes in daily.items():
            print(f"\n  {day}:")
            if dishes:
                for i, dish in enumerate(dishes, 1):
                    print(f"    {i}. {dish}")
            else:
                print("    (no dishes found)")
    except Exception as e:
        print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()

