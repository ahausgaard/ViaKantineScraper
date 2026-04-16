import re


def parse_week_number(text: str) -> str | None:
    """
    Return the week number string if the text looks like a canteen menu,
    otherwise return None.

    Expects lowercase input.
    """
    if "menu" not in text or "uge" not in text:
        return None

    match = re.search(r"uge\s*(\d+)", text)
    return match.group(1) if match else None

