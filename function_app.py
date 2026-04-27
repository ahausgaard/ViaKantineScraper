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


@app.timer_trigger(schedule="0 */4 * * * *", arg_name="warmTimer",
                   run_on_startup=False, use_monitor=False)
def keep_warm(warmTimer: func.TimerRequest) -> None:
    """Fires every 4 minutes to prevent cold starts on the consumption plan."""
    logging.info("Keep-warm ping.")


@app.timer_trigger(schedule="0 0 9 * * 0-6", arg_name="myTimer",
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


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Simple health check — open in a browser to confirm the function is running."""
    return func.HttpResponse("OK - canteen bot is alive", status_code=200)


@app.route(route="menu", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def slack_menu_command(req: func.HttpRequest) -> func.HttpResponse:
    """Handle the /menu Slack slash command.

    Usage:
      /menu          -> latest menu
      /menu 15       -> week 15 of current year
      /menu 15 2025  -> week 15 of 2025
    """
    logging.info("slack_menu_command: received request")

    try:
        timestamp = req.headers.get("X-Slack-Request-Timestamp", "")
        signature = req.headers.get("X-Slack-Signature", "")
        body = req.get_body().decode("utf-8")

        logging.info(f"slack_menu_command: timestamp='{timestamp}', sig_present={bool(signature)}, body_len={len(body)}")

        if not slack.verify_slack_signature(timestamp, body, signature):
            logging.warning("slack_menu_command: signature verification FAILED - returning 401")
            return func.HttpResponse("Unauthorized", status_code=401)

        logging.info("slack_menu_command: signature OK")

        params = parse_qs(body)
        command_text = params.get("text", [""])[0].strip()
        logging.info(f"slack_menu_command: command_text='{command_text}'")

        storage = StorageClient()

        if command_text:
            parts = command_text.split()
            try:
                week = int(parts[0])
                year = int(parts[1]) if len(parts) > 1 else datetime.now().isocalendar()[0]
            except ValueError:
                payload = slack.ephemeral_error_response(
                    "Invalid format. Use /menu, /menu 15, or /menu 15 2025."
                )
                return func.HttpResponse(json.dumps(payload), mimetype="application/json", status_code=200)

            logging.info(f"slack_menu_command: looking up week={week}, year={year}")
            result = storage.get_menu_for_week(week, year)
            if result is None:
                logging.info("slack_menu_command: no menu found for that week")
                payload = slack.ephemeral_error_response(f"No menu found for week {week}, {year}.")
            else:
                week_number, image_url = result
                logging.info(f"slack_menu_command: found menu for week {week_number}")
                payload = slack.ephemeral_menu_response(image_url, week_number)
        else:
            logging.info("slack_menu_command: looking up latest menu")
            result = storage.get_latest_menu_sas_url()
            if result is None:
                logging.info("slack_menu_command: no menu in storage")
                payload = slack.ephemeral_error_response("No menu available yet. Check back later!")
            else:
                week_number, image_url = result
                logging.info(f"slack_menu_command: returning week {week_number}")
                payload = slack.ephemeral_menu_response(image_url, week_number)

        logging.info("slack_menu_command: returning 200 with payload")
        return func.HttpResponse(json.dumps(payload), mimetype="application/json", status_code=200)

    except Exception as e:
        logging.exception(f"slack_menu_command: unhandled exception: {e}")
        payload = slack.ephemeral_error_response("Something went wrong on the server. Check the logs.")
        return func.HttpResponse(json.dumps(payload), mimetype="application/json", status_code=200)
