import os


def _positive_int(name: str, default: int) -> int:
    # base.py only catches ImportError around setup(), so a bad value must not
    # raise: it would stop the whole backend from starting.
    value = os.getenv(name, "").strip()
    if value.isdigit() and int(value) > 0:
        return int(value)
    if value:
        print(f"sheets_sync: {name} must be a positive number, got {value!r}.")
    return default


def setup(settings):
    """
    Called by baserow.config.settings.base for every installed plugin.
    """

    # How often every Google Sheets synced table pulls the sheet. Google allows 60
    # read requests per minute per user (sheets/api/limits).
    settings.SHEETS_SYNC_INTERVAL_MINUTES = _positive_int(
        "SHEETS_SYNC_INTERVAL_MINUTES", 5
    )
    # How often a failed push of a Baserow change to the sheet is retried, with an
    # exponential backoff, before it's given up and shown as the table's sync error.
    settings.SHEETS_SYNC_MAX_RETRIES = _positive_int("SHEETS_SYNC_MAX_RETRIES", 5)
