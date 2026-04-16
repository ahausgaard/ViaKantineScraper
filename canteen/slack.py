import hashlib
import hmac
import time

from canteen import config


def verify_slack_signature(timestamp: str, body: str, signature: str) -> bool:
    """Verify the request genuinely came from Slack using the signing secret."""
    try:
        if abs(time.time() - float(timestamp)) > 300:
            return False  # Replay attack guard (5 min window)
    except ValueError:
        return False

    signing_secret = config.get("SLACK_SIGNING_SECRET").encode()
    base = f"v0:{timestamp}:{body}".encode()
    expected = "v0=" + hmac.new(signing_secret, base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def ephemeral_menu_response(image_url: str, week_number: str) -> dict:
    """Build a Slack ephemeral response payload showing the menu image."""
    return {
        "response_type": "ephemeral",
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Canteen menu — Week {week_number}* 🍽️"},
            },
            {
                "type": "image",
                "image_url": image_url,
                "alt_text": f"Canteen menu week {week_number}",
            },
        ],
    }


def ephemeral_error_response(message: str) -> dict:
    return {"response_type": "ephemeral", "text": message}

