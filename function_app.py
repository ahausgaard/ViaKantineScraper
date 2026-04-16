import azure.functions as func
import logging

from canteen.storage import StorageClient
from canteen.scraper import fetch_image_urls
from canteen.ocr import extract_text
from canteen.menu_parser import parse_week_number

app = func.FunctionApp()


@app.timer_trigger(schedule="0 0 9 * * 1-5", arg_name="myTimer",
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
        today = storage.update_cooldown()
        logging.info(f"Saved Week {week_number} and set cooldown to {today}.")
        # Slack integration will trigger here
        break

