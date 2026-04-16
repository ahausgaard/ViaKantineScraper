import azure.functions as func
import json
import logging

from canteen.storage import StorageClient
from canteen.scraper import fetch_image_urls
from canteen.ocr import extract_text
from canteen.menu_parser import parse_week_number
from canteen import slack

app = func.FunctionApp()


@app.timer_trigger(schedule="0 0 9 * * 1-6", arg_name="myTimer",
                   run_on_startup=False, use_monitor=False)
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
    """Handle the /menu Slack slash command — responds ephemerally with the latest menu image."""
    timestamp = req.headers.get("X-Slack-Request-Timestamp", "")
    signature = req.headers.get("X-Slack-Signature", "")
    body = req.get_body().decode("utf-8")

    if not slack.verify_slack_signature(timestamp, body, signature):
        return func.HttpResponse("Unauthorized", status_code=401)

    storage = StorageClient()
    result = storage.get_latest_menu_sas_url()

    if result is None:
        payload = slack.ephemeral_error_response("No menu available yet. Check back later! 🥲")
    else:
        week_number, image_url = result
        payload = slack.ephemeral_menu_response(image_url, week_number)

    return func.HttpResponse(json.dumps(payload), mimetype="application/json", status_code=200)


