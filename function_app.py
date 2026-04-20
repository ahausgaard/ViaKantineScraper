import azure.functions as func
import json
import logging
from urllib.parse import parse_qs
from datetime import datetime

from canteen.storage import StorageClient
from canteen.scraper import fetch_image_urls
from canteen.ocr import extract_text
from canteen.menu_parser import parse_week_number
from canteen import slack

app = func.FunctionApp()



@app.timer_trigger(schedule="0 0 9 * * 1-6", arg_name="myTimer",
                   run_on_startup=True, use_monitor=False)
def check_canteen_menu(myTimer: func.TimerRequest) -> None:
    logging.info("Canteen Bot: Starting intelligent scan...")

    storage = StorageClient()

    if storage.is_on_cooldown():
        return

    for image_url in fetch_image_urls():
        text = extract_text(image_url)
        week_number = parse_week_number(text)

        if week_number is None:
            continue

        if storage.menu_exists(week_number):
            logging.info(f"Week {week_number} already in storage.")
            break

        logging.info(f"New menu found for Week {week_number}!")
        storage.save_menu(week_number, image_url)
        today = storage.update_cooldown(week_number)
        logging.info(f"Saved Week {week_number} and set cooldown until Friday {today}.")
        break


@app.route(route="menu", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def slack_menu_command(req: func.HttpRequest) -> func.HttpResponse:
    """Handle the /menu Slack slash command — responds ephemerally with the latest menu image.

    Usage:
      /menu          → latest menu
      /menu 15       → week 15 of current year
      /menu 15 2025  → week 15 of 2025
    """
    timestamp = req.headers.get("X-Slack-Request-Timestamp", "")
    signature = req.headers.get("X-Slack-Signature", "")
    body = req.get_body().decode("utf-8")

    if not slack.verify_slack_signature(timestamp, body, signature):
        return func.HttpResponse("Unauthorized", status_code=401)

    params = parse_qs(body)
    command_text = params.get("text", [""])[0].strip()

    storage = StorageClient()

    if command_text:
        parts = command_text.split()
        try:
            week = int(parts[0])
            year = int(parts[1]) if len(parts) > 1 else datetime.now().isocalendar()[0]
        except ValueError:
            payload = slack.ephemeral_error_response(
                "Invalid format. Use `/menu`, `/menu 15`, or `/menu 15 2025`."
            )
            return func.HttpResponse(json.dumps(payload), mimetype="application/json", status_code=200)

        result = storage.get_menu_for_week(week, year)
        if result is None:
            payload = slack.ephemeral_error_response(f"No menu found for week {week}, {year}. 🤷")
        else:
            week_number, image_url = result
            payload = slack.ephemeral_menu_response(image_url, week_number)
    else:
        result = storage.get_latest_menu_sas_url()
        if result is None:
            payload = slack.ephemeral_error_response("No menu available yet. Check back later! 🥲")
        else:
            week_number, image_url = result
            payload = slack.ephemeral_menu_response(image_url, week_number)

    return func.HttpResponse(json.dumps(payload), mimetype="application/json", status_code=200)

