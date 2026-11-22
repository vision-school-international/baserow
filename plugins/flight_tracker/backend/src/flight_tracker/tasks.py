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


# How often scheduled flight trackers are checked; each field's own interval
# decides which of its rows are looked up again.
TRACKER_TICK = timedelta(minutes=5)
# How long a fill holds its field, so asks while it runs don't repeat lookups.
LOCK_SECONDS = 60


def _tracker(field_id):
    from .models import FlightTrackerField

    return (
        FlightTrackerField.objects.filter(
            id=field_id,
            trashed=False,
            table__trashed=False,
            table__database__trashed=False,
            table__database__workspace__trashed=False,
        )
        .select_related("table__database__workspace", "flight_code_field")
        .first()
    )


@app.task(queue="export")
def fill_tracker(field_id: int, row_ids=None):
    """
    Fills a flight tracker field's cells (all rows, or `row_ids`): after it's set
    up, when flight numbers change, and for the rows on screen.
    """

    from django.core.cache import cache

    from .tracker import refresh_tracker

    field = _tracker(field_id)
    if field is None:
        return
    # Rows on screen are asked for again and again; one fill per field at once.
    lock = f"flight_tracker_fill_{field_id}"
    if row_ids is not None and not cache.add(lock, 1, LOCK_SECONDS):
        return
    try:
        refresh_tracker(field, row_ids)
    finally:
        if row_ids is not None:
            cache.delete(lock)


@app.task(queue="export")
def refresh_scheduled_trackers():
    """Looks up again the rows of scheduled trackers older than their interval."""

    from .flight import STOP_ERRORS
    from .models import REFRESH_SCHEDULE, FlightTrackerField
    from .tracker import refresh_tracker

    field_ids = FlightTrackerField.objects.filter(
        flight_refresh=REFRESH_SCHEDULE,
        trashed=False,
        table__trashed=False,
        table__database__trashed=False,
        table__database__workspace__trashed=False,
    ).values_list("id", flat=True)
    for field_id in field_ids:
        field = _tracker(field_id)
        if field is not None and refresh_tracker(field) in STOP_ERRORS:
            return


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        timedelta(minutes=settings.FLIGHT_TRACKER_INTERVAL_MINUTES),
        refresh_scheduled_flights.s(),
    )
    sender.add_periodic_task(TRACKER_TICK, refresh_scheduled_trackers.s())
