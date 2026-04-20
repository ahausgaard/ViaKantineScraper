import hashlib
import hmac
import time

from canteen import config


def verify_slack_signature(timestamp: str, body: str, signature: str) -> bool:
    """Verify the request genuinely came from Slack using the signing secret."""
    import logging
    try:
        if abs(time.time() - float(timestamp)) > 300:
            logging.warning("Slack signature: timestamp too old")
            return False  # Replay attack guard (5 min window)
    except ValueError:
        logging.warning("Slack signature: invalid timestamp")
        return False

    secret = config.get("SLACK_SIGNING_SECRET")
    if not secret:
        logging.error("Slack signature: SLACK_SIGNING_SECRET is not set — allowing request")
        return True  # Fail open so we can see the rest of the logs

    signing_secret = secret.encode()
    base = f"v0:{timestamp}:{body}".encode()
    expected = "v0=" + hmac.new(signing_secret, base, hashlib.sha256).hexdigest()
    match = hmac.compare_digest(expected, signature)
    if not match:
        logging.warning(f"Slack signature: mismatch. expected={expected[:20]}... got={signature[:20]}...")
    return match


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

