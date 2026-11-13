from django.conf import settings
from django.db import models

from baserow.contrib.database.data_sync.models import DataSync


class GoogleSheetsDataSync(DataSync):
    """Same shape as core's ICalCalendarDataSync and PostgreSQLDataSync."""

    google_service_account_key = models.TextField(
        help_text="The JSON key of the Google service account the sheet is shared "
        "with. Write only."
    )
    google_spreadsheet_id = models.CharField(
        max_length=2000, help_text="The spreadsheet ID or its URL."
    )
    google_sheet_name = models.CharField(
        max_length=255, help_text="The name of the tab in the spreadsheet."
    )
    google_id_column = models.CharField(
        max_length=255,
        help_text="The header of the column that holds a unique ID for every row.",
    )
    authorized_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        help_text="The user on whose behalf the periodic sync runs.",
    )


class GoogleSheetsPendingRow(models.Model):
    """
    A Baserow row created in a two-way synced table that isn't written to the sheet
    yet. A pull keeps it, so it's not deleted as missing from the sheet. Its own
    table, because core saves the whole DataSync (data_sync/handler.py:752) and
    would overwrite a list kept on it.
    """

    data_sync = models.ForeignKey(
        GoogleSheetsDataSync, on_delete=models.CASCADE, related_name="pending_rows"
    )
    row_id = models.PositiveIntegerField()

    class Meta:
        unique_together = [["data_sync", "row_id"]]
