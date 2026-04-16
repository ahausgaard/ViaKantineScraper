import logging
import requests
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient

from canteen import config

CONTAINER_NAME = "canteen-menus"
COOLDOWN_BLOB = "last_success.txt"
COOLDOWN_DAYS = 3


class StorageClient:
    def __init__(self):
        connection_string = config.get("AzureWebJobsStorage")
        self._client = BlobServiceClient.from_connection_string(connection_string)

    def _blob(self, name: str):
        return self._client.get_blob_client(container=CONTAINER_NAME, blob=name)

    # --- Cooldown ---

    def is_on_cooldown(self) -> bool:
        blob = self._blob(COOLDOWN_BLOB)
        if not blob.exists():
            return False

        last_date_str = blob.download_blob().readall().decode("utf-8")
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")

        if datetime.now() < last_date + timedelta(days=COOLDOWN_DAYS):
            logging.info(f"Cooldown active. Last menu found on {last_date_str}. See you in a few days!")
            return True

        return False

    def update_cooldown(self) -> str:
        today_str = datetime.now().strftime("%Y-%m-%d")
        self._blob(COOLDOWN_BLOB).upload_blob(today_str, overwrite=True)
        return today_str

    # --- Menu blobs ---

    def menu_exists(self, week_number: str) -> bool:
        return self._blob(f"menu_week{week_number}.jpg").exists()

    def save_menu(self, week_number: str, image_url: str) -> None:
        image_data = requests.get(image_url).content
        self._blob(f"menu_week{week_number}.jpg").upload_blob(image_data)

