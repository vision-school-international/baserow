from datetime import timedelta

from django.conf import settings

from loguru import logger

from baserow.config.celery import app


@app.task(queue="export")
def refresh_scheduled_flights():
    """Looks up the flights of every flight field set to refresh on a schedule."""

    from .flight import STOP_ERRORS, refresh
    from .models import REFRESH_SCHEDULE, FlightField

    # Slightly less than the interval, so each run refreshes what the last one did.
    max_age = timedelta(minutes=settings.FLIGHT_TRACKER_INTERVAL_MINUTES * 0.9)
    fields = FlightField.objects.filter(
        flight_refresh=REFRESH_SCHEDULE,
        trashed=False,
        table__trashed=False,
        table__database__trashed=False,
        table__database__workspace__trashed=False,
    ).select_related("table")
    for field in fields:
        model = field.table.get_model(fields=[field], field_ids=[])
        flights_by_row = dict(
            model.objects.exclude(**{f"{field.db_column}__in": [""]})
            .exclude(**{f"{field.db_column}__isnull": True})
            .values_list("id", field.db_column)
        )
        _, error = refresh(field, flights_by_row, max_age=max_age)
        if error:
            logger.warning("Flight field {id}: AirLabs said {e}.", id=field.id, e=error)
            if error in STOP_ERRORS:
                return


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        timedelta(minutes=settings.FLIGHT_TRACKER_INTERVAL_MINUTES),
        refresh_scheduled_flights.s(),
    )
