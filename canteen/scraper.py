import logging
from apify_client import ApifyClient

from canteen import config

FACEBOOK_URL = "https://www.facebook.com/VIAKantinenHorsens"
ACTOR_ID = "apify/facebook-photos-scraper"
RESULTS_LIMIT = 5


def fetch_image_urls() -> list[str]:
    """Run the Apify scraper and return a list of image URLs from the latest posts."""
    client = ApifyClient(config.get("APIFY_API_TOKEN"))
    run_input = {
        "startUrls": [{"url": FACEBOOK_URL}],
        "resultsLimit": RESULTS_LIMIT,
    }

    logging.info("Running Scraper...")
    run = client.actor(ACTOR_ID).call(run_input=run_input)
    items = client.dataset(run.default_dataset_id).list_items().items

    return [item["image"] for item in items if item.get("image")]

