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
