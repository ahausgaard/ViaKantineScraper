import logging
import requests
from datetime import datetime, timedelta, timezone
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

from canteen import config

CONTAINER_NAME = "canteen-menus"
COOLDOWN_BLOB = "last_success.txt"


def _friday_of_week(week_number: int, year: int | None = None) -> datetime:
    """Return end-of-day Friday of the given ISO week number."""
    if year is None:
        year = datetime.now().isocalendar()[0]
    return datetime.fromisocalendar(year, week_number, 5).replace(
        hour=23, minute=59, second=59
    )


def _blob_name(week_number: int | str, year: int | str) -> str:
    return f"menu_week{week_number}_year{year}.jpg"


class StorageClient:
    def __init__(self):
        connection_string = config.get("AzureWebJobsStorage")
        self._client = BlobServiceClient.from_connection_string(connection_string)

    def _blob(self, name: str):
        return self._client.get_blob_client(container=CONTAINER_NAME, blob=name)

    def _make_sas_url(self, blob_name: str) -> str:
        account = self._client.account_name
        account_key = self._client.credential.account_key
        sas = generate_blob_sas(
            account_name=account,
            container_name=CONTAINER_NAME,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        return f"https://{account}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}?{sas}"

    # --- Cooldown ---

    def is_on_cooldown(self) -> bool:
        blob = self._blob(COOLDOWN_BLOB)
        if not blob.exists():
            return False

        cooldown_str = blob.download_blob().readall().decode("utf-8")
        cooldown_until = datetime.strptime(cooldown_str, "%Y-%m-%d")

        if datetime.now() < cooldown_until:
            logging.info(f"Cooldown active until {cooldown_str} (Friday of last found week).")
            return True

        return False

    def update_cooldown(self, week_number: str) -> str:
        """Set cooldown to the Friday of the given menu week."""
        friday = _friday_of_week(int(week_number))
        friday_str = friday.strftime("%Y-%m-%d")
        self._blob(COOLDOWN_BLOB).upload_blob(friday_str, overwrite=True)
        return friday_str

    # --- Menu blobs ---

    def menu_exists(self, week_number: str) -> bool:
        year = datetime.now().isocalendar()[0]
        return self._blob(_blob_name(week_number, year)).exists()

    def save_menu(self, week_number: str, image_url: str) -> None:
        year = datetime.now().isocalendar()[0]
        image_data = requests.get(image_url).content
        self._blob(_blob_name(week_number, year)).upload_blob(image_data)

    def get_menu_for_week(self, week_number: int, year: int) -> tuple[str, str] | None:
        """Return (week_number, sas_url) for a specific week/year, or None if not stored."""
        name = _blob_name(week_number, year)
        if not self._blob(name).exists():
            return None
        return str(week_number), self._make_sas_url(name)

    def get_latest_menu_sas_url(self, lookback_weeks: int = 4) -> tuple[str, str] | None:
        """Find the most recent stored menu and return (week_number, sas_url), or None."""
        iso = datetime.now().isocalendar()
        current_week, current_year = iso[1], iso[0]

        for offset in range(lookback_weeks):
            week = current_week - offset
            year = current_year
            if week < 1:
                week += 52
                year -= 1

            name = _blob_name(week, year)
            if not self._blob(name).exists():
                continue

            return str(week), self._make_sas_url(name)

        return None
