import azure.functions as func
import logging
import os
import requests
import re
from datetime import datetime, timedelta
from apify_client import ApifyClient
from azure.storage.blob import BlobServiceClient
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

app = func.FunctionApp()


@app.timer_trigger(schedule="0 0 9 * * 1-5", arg_name="myTimer",
                   run_on_startup=False, use_monitor=False)
def check_canteen_menu(myTimer: func.TimerRequest) -> None:
    logging.info('Canteen Bot: Starting intelligent scan...')

    # 1. Setup Storage Client
    storage_connection = os.environ.get("AzureWebJobsStorage")
    blob_service_client = BlobServiceClient.from_connection_string(
        storage_connection)
    container_name = "canteen-menus"

    # 2. COOLDOWN CHECK: Check if we successfully found a menu recently
    cooldown_blob = blob_service_client.get_blob_client(
        container=container_name, blob="last_success.txt")

    if cooldown_blob.exists():
        last_date_str = cooldown_blob.download_blob().readall().decode('utf-8')
        last_date = datetime.strptime(last_date_str, '%Y-%m-%d')

        if datetime.now() < last_date + timedelta(days=3):
            logging.info(
                f"Cooldown active. Last menu found on {last_date_str}. See you in a few days!")
            return

    # 3. Configuration & Scraper
    apify_token = os.environ.get("APIFY_API_TOKEN")
    vision_key = os.environ.get("VISION_KEY")
    vision_endpoint = os.environ.get("VISION_ENDPOINT")

    client = ApifyClient(apify_token)
    run_input = {
        "startUrls": [{"url": "https://www.facebook.com/VIAKantinenHorsens"}],
        "resultsLimit": 5}

    logging.info("Running Scraper...")
    run = client.actor("crawlerbros/facebook-photos-scraper").call(
        run_input=run_input)
    items = client.dataset(run["defaultDatasetId"]).list_items().items

    cv_client = ImageAnalysisClient(endpoint=vision_endpoint,
                                    credential=AzureKeyCredential(vision_key))

    for item in items:
        image_url = item.get("imageUrl")
        if not image_url: continue

        # 4. OCR Analysis
        result = cv_client.analyze_from_url(image_url=image_url,
                                            visual_features=[
                                                VisualFeatures.READ])
        extracted_text = ""
        if result.read is not None and len(result.read.blocks) > 0:
            for line in result.read.blocks[0].lines:
                extracted_text += line.text + " "

        extracted_text = extracted_text.lower()

        # 5. Filter for Menu + Week Number
        if "menu" in extracted_text and "uge" in extracted_text:
            week_match = re.search(r'uge\s*(\d+)', extracted_text)
            if not week_match: continue

            week_number = week_match.group(1)
            blob_name = f"menu_week{week_number}.jpg"
            menu_blob = blob_service_client.get_blob_client(
                container=container_name, blob=blob_name)

            if not menu_blob.exists():
                logging.info(f"New menu found for Week {week_number}!")

                # Upload the image
                image_data = requests.get(image_url).content
                menu_blob.upload_blob(image_data)

                # UPDATE COOLDOWN: Save today's date to the cloud
                today_str = datetime.now().strftime('%Y-%m-%d')
                cooldown_blob.upload_blob(today_str, overwrite=True)

                logging.info(
                    f"Saved Week {week_number} and set cooldown to {today_str}.")
                # Slack integration will trigger here
                break
            else:
                logging.info(f"Week {week_number} already in storage.")
                break