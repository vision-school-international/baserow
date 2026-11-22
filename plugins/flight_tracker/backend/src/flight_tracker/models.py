from django.conf import settings
from django.db import models

from baserow.contrib.database.fields.models import Field, TextField

REFRESH_VIEW = "view"
REFRESH_SCHEDULE = "schedule"
REFRESH_CHOICES = [
    (REFRESH_VIEW, "When viewed"),
    (REFRESH_SCHEDULE, "On a schedule"),
]


class FlightField(TextField):
    """
    A flight number, like "AA6" or "AAL6", stored as upper case text so the
    cells, filters and sorting are the core text ones. Its live status is kept in
    FlightStatus, not in the cell.

    Don't uninstall the plugin while flight fields exist: their tables stop
    loading until they're converted to text first.
    """

    flight_refresh = models.CharField(
        max_length=8,
        choices=REFRESH_CHOICES,
        default=REFRESH_VIEW,
        help_text="Look the flights up when they're viewed, or on a schedule.",
    )


class FlightStatus(models.Model):
    """The last AirLabs lookup of one cell of a flight field."""

    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    # No foreign key: rows live in each table's own generated table.
    row_id = models.PositiveIntegerField()
    # The cell's value when it was looked up; a changed cell is looked up again.
    flight = models.CharField(max_length=16)
    # The AirLabs fields of flight.KEPT_FIELDS, or {"error": code}.
    data = models.JSONField(default=dict)
    fetched_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["field", "row_id"], name="flight_status_field_row"
            )
        ]


MIN_INTERVAL_MINUTES = 5
MAX_INTERVAL_MINUTES = 7 * 24 * 60


class FlightTrackerField(Field):
    """
    Read-only JSON with the live AirLabs data of the flight number in another
    field of the row (`flight_code_field`), for people and for apps (tracker.py
    to_cell). Each row's last lookup is kept in FlightStatus.
    """

    flight_code_field = models.ForeignKey(
        Field,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="The field of the same table holding the flight number.",
    )
    flight_refresh = models.CharField(
        max_length=8,
        choices=REFRESH_CHOICES,
        default=REFRESH_VIEW,
        help_text="Look the flights up when they're viewed, or on a schedule.",
    )
    flight_interval_minutes = models.PositiveIntegerField(
        default=30,
        help_text="How old a row's flight data may get before it's looked up again.",
    )
    # Like ai_tables' ai_auto_update_user: who the updates are made as.
    flight_tracker_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="The user the flight data is written as: who set the field up.",
    )
