import os


def setup(settings):
    """
    Called by baserow.config.settings.base for every installed plugin.
    """

    # How often every Google Sheets synced table pulls the sheet. Google allows 60
    # read requests per minute per user (sheets/api/limits).
    settings.SHEETS_SYNC_INTERVAL_MINUTES = int(
        os.getenv("SHEETS_SYNC_INTERVAL_MINUTES", "") or 5
    )
    # How often a failed push of a Baserow change to the sheet is retried, with an
    # exponential backoff, before it's given up and shown as the table's sync error.
    settings.SHEETS_SYNC_MAX_RETRIES = int(
        os.getenv("SHEETS_SYNC_MAX_RETRIES", "") or 5
    )
