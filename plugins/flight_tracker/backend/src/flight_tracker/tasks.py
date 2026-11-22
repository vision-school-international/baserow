import uuid
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache

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
# AirLabs calls one ask from the rows on screen may make, and how long it may
# spend on them; the rest wait for the next ask (like views.py MAX_LOOKUPS).
ON_SCREEN_MAX_LOOKUPS = 20
ON_SCREEN_MAX_SECONDS = 8
# Longer than a run can take: 20 lookups of at most (3 + 5) seconds each.
LOCK_SECONDS = 15 * 60


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


class _Lock:
    """A cache lock only its holder releases, so an expired lock that another
    run took isn't deleted from under it."""

    def __init__(self, key):
        self.key, self.token = key, uuid.uuid4().hex

    def __enter__(self):
        return cache.add(self.key, self.token, LOCK_SECONDS)

    def __exit__(self, *exc):
        if cache.get(self.key) == self.token:
            cache.delete(self.key)


@app.task(queue="export")
def fill_tracker(field_id: int, row_ids=None, on_screen=False):
    """
    Fills a flight tracker field's cells (all rows, or `row_ids`): after it's set
    up and when flight numbers change (never skipped), and for the rows on screen
    (`on_screen`: bounded, and skipped while another one runs for the field).
    """

    from .models import REFRESH_VIEW
    from .tracker import refresh_tracker

    field = _tracker(field_id)
    if field is None:
        return
    if not on_screen:
        refresh_tracker(field, row_ids)
        return
    with _Lock(f"flight_tracker_on_screen_{field_id}") as locked:
        if locked:
            refresh_tracker(
                field,
                row_ids,
                max_lookups=ON_SCREEN_MAX_LOOKUPS,
                max_seconds=ON_SCREEN_MAX_SECONDS,
                # Scheduled trackers are kept fresh by the schedule; on screen
                # they only fill new or changed flights.
                include_stale=field.flight_refresh == REFRESH_VIEW,
            )


@app.task(queue="export")
def refresh_scheduled_trackers():
    """Looks up again the rows of scheduled trackers older than their interval."""

    from .flight import STOP_ERRORS
    from .models import REFRESH_SCHEDULE, FlightTrackerField
    from .tracker import refresh_tracker

    with _Lock("flight_tracker_schedule") as locked:
        if not locked:
            return  # The last run is still going.
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
