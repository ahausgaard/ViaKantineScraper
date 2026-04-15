import azure.functions as func
import logging
import os
import requests
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

    # Configuration
    apify_token = os.environ.get("APIFY_API_TOKEN")
    storage_connection = os.environ.get("AzureWebJobsStorage")
    vision_key = os.environ.get("VISION_KEY")
    vision_endpoint = os.environ.get("VISION_ENDPOINT")

    # 1. Start Apify Scraper
    # 1. Start Apify Scraper with strict limits
    client = ApifyClient(apify_token)
    run_input = {
        "startUrls": [{"url": "https://www.facebook.com/VIAKantinenHorsens"}],
        "resultsLimit": 5,  # Hard limit on returned items
        "onlyPostsAfter": "2026-04-01",  # Optional: Only look at this month
        "scrapeSelectedIds": False
    }

    logging.info("Running Apify scraper with a limit of 5 photos...")
    # Using the 'actor' call but ensuring we target the latest photos
    run = client.actor("crawlerbros/facebook-photos-scraper").call(
        run_input=run_input)
    items = client.dataset(run["defaultDatasetId"]).list_items().items

    # 2. Setup Azure AI Vision Client
    cv_client = ImageAnalysisClient(endpoint=vision_endpoint,
                                    credential=AzureKeyCredential(vision_key))

    for item in items:
        image_url = item.get("imageUrl")
        item_id = item.get("id") or item.get("image_url_hash") or "latest"

        logging.info(f"Analyzing image: {image_url}")

        # 3. Ask Azure AI to read the text (OCR)
        result = cv_client.analyze_from_url(
            image_url=image_url,
            visual_features=[VisualFeatures.READ]
        )

        # Extract all text found in the image
        extracted_text = ""
        if result.read is not None:
            for line in result.read.blocks[0].lines:
                extracted_text += line.text + " "

        extracted_text = extracted_text.lower()
        logging.info(
            f"OCR found text: {extracted_text[:100]}...")  # Log first 100 chars

        # 4. Check for keywords (Menu detection)
        keywords = ["menu", "mandag", "tirsdag", "onsdag", "torsdag", "fredag",
                    "uge"]
        if any(word in extracted_text for word in keywords):
            logging.info("Bingo! This image contains a menu.")

            # 5. Upload to Storage
            blob_name = f"menu_{item_id}.jpg"
            blob_service_client = BlobServiceClient.from_connection_string(
                storage_connection)
            blob_client = blob_service_client.get_blob_client(
                container="canteen-menus", blob=blob_name)

            if not blob_client.exists():
                image_data = requests.get(image_url).content
                blob_client.upload_blob(image_data)
                logging.info(f"New menu saved to cloud: {blob_name}")

                # TODO: Send to Slack here!
                break  # We found the menu, no need to check the other 4 posts
            else:
                logging.info("Menu already exists in storage. Skipping.")
                break
        else:
            logging.info("Image did not look like a menu. Checking next...")