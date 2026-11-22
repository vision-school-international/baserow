"""
Fills the flight tracker field (FlightTrackerField): JSON with the AirLabs data
of the flight number in the row's flight code field.
"""

import re
import time
from datetime import UTC, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from loguru import logger

from baserow.contrib.database.rows.handler import RowHandler
from baserow.contrib.database.table.operations import (
    ListRowsDatabaseTableOperationType,
)
from baserow.core.handler import CoreHandler

from .flight import IATA, ICAO, STOP_ERRORS, FlightLookupError, lookup
from .models import FlightStatus

SCHEMA_VERSION = 1
# The types a flight number can be read from: their cells are plain text.
CODE_FIELD_TYPES = {"text", "long_text", "flight", "pattern_text"}
# Rows written (and locked) in one transaction.
WRITE_BATCH = 200


def flight_code(value):
    """The flight number in a code field's value ("aa 6" -> "AA6"), or ''."""

    if value is None:
        return ""
    return re.sub(r"\s+", "", str(value)).upper()


def is_flight(code):
    return bool(ICAO.fullmatch(code) or IATA.fullmatch(code))


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _place(data, side):
    """One end of the flight. Times are the airport's local time, plus UTC."""

    def get(key):
        return data.get(f"{side}_{key}")

    place = {
        "airport_iata": get("iata"),
        "airport_icao": get("icao"),
        "airport_name": get("name"),
        "city": get("city"),
        "country": get("country"),
        "terminal": get("terminal"),
        "gate": get("gate"),
        "scheduled": get("time"),
        "scheduled_utc": get("time_utc"),
        "estimated": get("estimated"),
        "estimated_utc": get("estimated_utc"),
        "actual": get("actual"),
        "actual_utc": get("actual_utc"),
        "delay_minutes": _int(get("delayed")),
    }
    if side == "arr":
        place["baggage"] = get("baggage")
    return place


def to_cell(code, data):
    """
    The cell's JSON. Every key is always there, null when AirLabs (or its plan)
    doesn't give it, so apps can rely on the shape. `error` is null, or
    "not_found" (AirLabs knows no current flight) or "invalid_flight_number".
    """

    data = data or {}
    error = data.get("error")
    updated = _int(data.get("updated"))
    return {
        "schema": SCHEMA_VERSION,
        "flight": code,
        "error": error,
        "status": None if error else data.get("status"),
        "flight_iata": data.get("flight_iata"),
        "flight_icao": data.get("flight_icao"),
        "flight_number": data.get("flight_number"),
        "airline_iata": data.get("airline_iata"),
        "airline_icao": data.get("airline_icao"),
        "airline_name": data.get("airline_name"),
        "codeshare_flight_iata": data.get("cs_flight_iata"),
        "departure": _place(data, "dep"),
        "arrival": _place(data, "arr"),
        "duration_minutes": _int(data.get("duration")),
        "progress_percent": _int(data.get("percent")),
        "aircraft_icao": data.get("aircraft_icao"),
        "aircraft_registration": data.get("reg_number"),
        # When AirLabs last had a signal from the aircraft.
        "position_updated_at": (
            datetime.fromtimestamp(updated, tz=UTC).isoformat() if updated else None
        ),
    }


def _may_write(field):
    """The user the data is written as, if they may still update the table."""

    from baserow.contrib.database.rows.operations import (
        UpdateDatabaseRowOperationType,
    )

    user = field.flight_tracker_user
    if user is None or not user.is_active:
        return None
    table = field.table
    for operation in (
        ListRowsDatabaseTableOperationType.type,
        UpdateDatabaseRowOperationType.type,
    ):
        if not CoreHandler().check_permissions(
            user,
            operation,
            workspace=table.database.workspace,
            context=table,
            raise_permission_exceptions=False,
        ):
            return None
    return user


def refresh_tracker(
    field, row_ids=None, max_lookups=None, max_seconds=None, include_stale=True
):
    """
    Fills the field's cells of `row_ids` (all rows if None): looks up flights
    whose row has no data yet, whose flight number changed, or, with
    `include_stale`, whose data is older than the field's interval, and writes
    the cells whose JSON changed.
    Each flight number is looked up once. Returns the AirLabs error code that
    stopped the lookups, if any.
    """

    code_field = field.flight_code_field
    # Checked again here: the code field may have been converted since.
    if (
        code_field is None
        or code_field.trashed
        or code_field.get_type().type not in CODE_FIELD_TYPES
    ):
        return None
    user = _may_write(field)
    if user is None:
        return None

    table = field.table
    model = table.get_model()
    queryset = model.objects.all()
    if row_ids is not None:
        queryset = queryset.filter(id__in=row_ids)
    rows = list(queryset.values_list("id", code_field.db_column, field.db_column))
    if not rows:
        return None

    now = timezone.now()
    max_age = timedelta(minutes=field.flight_interval_minutes)
    statuses = {
        s.row_id: s
        for s in FlightStatus.objects.filter(
            field=field, row_id__in=[row_id for row_id, _, _ in rows]
        )
    }

    def is_due(row_id, code):
        status = statuses.get(row_id)
        return (
            status is None
            or status.flight != code
            or (include_stale and status.fetched_at < now - max_age)
        )

    codes = {row_id: flight_code(value) for row_id, value, _ in rows}
    due = sorted({c for r, c in codes.items() if is_flight(c) and is_due(r, c)})

    results, error = {}, None
    started = time.monotonic()
    for code in due[:max_lookups]:
        if max_seconds is not None and time.monotonic() - started > max_seconds:
            break
        try:
            results[code] = lookup(code)
        except FlightLookupError as exc:
            error = exc.code
            if exc.code in STOP_ERRORS:
                break

    # row_id -> (flight number, new cell, looked up now, cell changed)
    pending = {}
    for row_id, _, cell in rows:
        code = codes[row_id]
        if not code:
            new = None
        elif not is_flight(code):
            new = to_cell(code, {"error": "invalid_flight_number"})
        elif code in results:
            new = to_cell(code, results[code])
        elif cell and cell.get("flight") == code:
            continue  # Not due, or AirLabs couldn't answer: the data stays.
        else:
            # A new flight number that couldn't be looked up yet.
            new = to_cell(code, {})
        looked_up = code in results
        if new != cell or looked_up:
            pending[row_id] = (code, new, looked_up, new != cell)

    # In batches, so a big table's rows aren't all locked while people edit.
    items = list(pending.items())
    for i in range(0, len(items), WRITE_BATCH):
        _write(field, user, model, code_field, dict(items[i : i + WRITE_BATCH]), now)
    if error:
        logger.warning("Flight tracker {id}: AirLabs said {e}.", id=field.id, e=error)
    return error


def _write(field, user, model, code_field, pending, now):
    """
    Writes the cells and stamps the lookups in one transaction: force_update_rows
    locks the rows (select_for_update), and a failed write leaves the rows due.
    """

    with transaction.atomic():
        # Under the row locks: a row whose flight number changed during the
        # lookups is left to the fill that change scheduled (field_types.py).
        current = dict(
            model.objects.select_for_update()
            .filter(id__in=list(pending))
            .values_list("id", code_field.db_column)
        )
        updates, stamped = [], []
        for row_id, (code, new, looked_up, changed) in pending.items():
            if row_id not in current or flight_code(current[row_id]) != code:
                continue
            if changed:
                updates.append({"id": row_id, f"field_{field.id}": new})
            if looked_up:
                stamped.append((row_id, code))
        if updates:
            # The value is managed here, so it's written past the read-only
            # check, like data sync (rows/handler.py force_update_rows).
            RowHandler().force_update_rows(
                user, field.table, updates, model=model, values_already_prepared=True
            )
        for row_id, code in stamped:
            FlightStatus.objects.update_or_create(
                field=field,
                row_id=row_id,
                defaults={"flight": code, "data": {}, "fetched_at": now},
            )


STATUS_NAMES = {"scheduled": "Scheduled", "en-route": "In the air", "landed": "Landed"}


def summary(cell):
    """One line for exports to text, search and the agent: the cell's JSON is
    the full data."""

    if cell.get("error") == "not_found":
        return f"{cell.get('flight')}: flight not found"
    if cell.get("error") == "invalid_flight_number":
        return f"{cell.get('flight')}: not a flight number"

    def end(place):
        time = place.get("actual") or place.get("estimated") or place.get("scheduled")
        return " ".join(
            x for x in (place.get("airport_iata"), (time or "")[11:16]) if x
        )

    dep, arr = cell.get("departure") or {}, cell.get("arrival") or {}
    route = " → ".join(x for x in (end(dep), end(arr)) if x)
    gate = f"Gate {dep['gate']}" if dep.get("gate") else ""
    status = STATUS_NAMES.get(cell.get("status"), cell.get("status") or "")
    return " · ".join(x for x in (cell.get("flight"), status, route, gate) if x)
