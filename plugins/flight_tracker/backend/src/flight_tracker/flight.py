"""
AirLabs Flight Information API (https://airlabs.co/docs/flight): the one closest
live, scheduled or landed flight of a flight number. It takes no date.
"""

import os
import re
import time
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone

import requests

# Set in the server's env, never in the code: this repository is on GitHub.
API_KEY = os.getenv("AIRLABS_API_KEY", "").strip()
API_URL = "https://airlabs.co/api/v9/flight"
# (connect, read): a slow AirLabs mustn't hold a web worker.
TIMEOUT_SECONDS = (3, 5)

# The ICAO airline code is 3 letters ("AAL6"); the IATA one is 2 characters, at
# most one a digit ("AA6", "F9123", "9W1"), so a bare number like "878" is no
# flight. Both are followed by a 1-4 digit number and maybe a letter.
ICAO = re.compile(r"[A-Z]{3}\d{1,4}[A-Z]?")
IATA = re.compile(r"(?:[A-Z][A-Z0-9]|[0-9][A-Z])\d{1,4}[A-Z]?")

# What the flight field (FlightField) keeps of a lookup; the tracker field keeps
# more (tracker.py to_cell). Fields the AirLabs plan doesn't include are missing.
KEPT_FIELDS = (
    "flight_iata",
    "flight_icao",
    "status",
    "dep_iata",
    "dep_terminal",
    "dep_gate",
    "dep_time",
    "dep_estimated",
    "dep_actual",
    "dep_delayed",
    "arr_iata",
    "arr_terminal",
    "arr_gate",
    "arr_baggage",
    "arr_time",
    "arr_estimated",
    "arr_actual",
    "arr_delayed",
    "updated",
)

# AirLabs error codes (https://airlabs.co/docs/, "Common Errors") after which no
# more flights are looked up in the same run: every lookup would fail the same way.
STOP_ERRORS = {
    "unknown_api_key",
    "expired_api_key",
    "minute_limit_exceeded",
    "hour_limit_exceeded",
    "month_limit_exceeded",
    "no_api_key",
    "unavailable",
    "local_day_limit",
}


class FlightLookupError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def clean_flight(value):
    """'aa 6' -> 'AA6'. Empty stays empty; anything else that isn't a flight
    number is refused."""

    if value is None:
        return None
    flight = re.sub(r"\s+", "", str(value)).upper()
    if flight and not (ICAO.fullmatch(flight) or IATA.fullmatch(flight)):
        raise ValidationError(
            f"'{value}' isn't a flight number, like AA6 or AAL6.", code="invalid"
        )
    return flight


def lookup(flight):
    """
    The flight as AirLabs answers it, or {"error": "not_found"}. Raises
    FlightLookupError when AirLabs can't answer now (key, limits, network), so
    the last good status isn't overwritten.
    """

    if not API_KEY:
        raise FlightLookupError("no_api_key")
    # One limit for the whole server, so no user or schedule can use up the
    # AirLabs plan; the cache is shared by the web and celery workers.
    bucket = f"flight_tracker_lookups_{int(time.time() // 86400)}"
    cache.add(bucket, 0, timeout=86400)
    if cache.incr(bucket) > settings.FLIGHT_TRACKER_MAX_LOOKUPS_PER_DAY:
        raise FlightLookupError("local_day_limit")
    param = "flight_icao" if ICAO.fullmatch(flight) else "flight_iata"
    # The key is in the query string as AirLabs documents. Sentry, which records
    # outgoing URLs, isn't configured on this server (no SENTRY_DSN).
    try:
        response = requests.get(
            API_URL,
            params={param: flight, "api_key": API_KEY},
            timeout=TIMEOUT_SECONDS,
        )
        body = response.json()
    except (requests.RequestException, ValueError):
        raise FlightLookupError("unavailable")

    # Errors are {"error": {"message", "code"}} (https://airlabs.co/docs/).
    error = body.get("error") if isinstance(body, dict) else None
    if error:
        code = error.get("code") if isinstance(error, dict) else str(error)
        if code == "not_found":
            return {"error": "not_found"}
        raise FlightLookupError(code or "unavailable")
    # A real answer wraps the flight in "response" (checked 2026-11-22); the docs
    # show it bare, so both are read.
    flight_data = body.get("response", body) if isinstance(body, dict) else None
    if not isinstance(flight_data, dict) or not flight_data:
        return {"error": "not_found"}
    return flight_data


def serialize_status(status):
    return {
        "flight": status.flight,
        "fetched_at": status.fetched_at.isoformat(),
        **status.data,
    }


def refresh(field, flights_by_row, max_age=None, max_lookups=None, max_seconds=None):
    """
    Looks up the flights of `flights_by_row` ({row_id: flight}) that have no
    status yet, whose cell changed, or, with `max_age`, whose status is older.
    Each flight number is looked up once. Returns ({row_id: status}, error), the
    error being the AirLabs code that stopped the lookups, if any. With
    `max_seconds`, no lookup starts after that long; the rest wait.
    """

    from .models import FlightStatus

    # Cells converted from other types keep their old text (core runs no
    # prepare_value_for_db then); only real flight numbers go to AirLabs.
    flights_by_row = {
        row_id: flight
        for row_id, flight in flights_by_row.items()
        if flight and (ICAO.fullmatch(flight) or IATA.fullmatch(flight))
    }
    now = timezone.now()
    statuses = {
        s.row_id: s
        for s in FlightStatus.objects.filter(field=field, row_id__in=flights_by_row)
    }

    def is_due(row_id, flight):
        status = statuses.get(row_id)
        if status is None or status.flight != flight:
            return True
        return max_age is not None and status.fetched_at < now - max_age

    due = {f for row_id, f in flights_by_row.items() if f and is_due(row_id, f)}
    results, error = {}, None
    started = time.monotonic()
    for flight in sorted(due)[:max_lookups]:
        if max_seconds is not None and time.monotonic() - started > max_seconds:
            break
        try:
            data = lookup(flight)
            results[flight] = {k: data[k] for k in (*KEPT_FIELDS, "error") if k in data}
        except FlightLookupError as exc:
            error = exc.code
            if exc.code in STOP_ERRORS:
                break

    for row_id, flight in flights_by_row.items():
        if flight in results:
            status, _ = FlightStatus.objects.update_or_create(
                field=field,
                row_id=row_id,
                defaults={"flight": flight, "data": results[flight], "fetched_at": now},
            )
            statuses[row_id] = status

    return {
        row_id: serialize_status(statuses[row_id])
        for row_id, flight in flights_by_row.items()
        # A status of an older value of the cell isn't shown.
        if flight and row_id in statuses and statuses[row_id].flight == flight
    }, error


def view_max_age():
    from django.conf import settings

    return timedelta(minutes=settings.FLIGHT_TRACKER_VIEW_TTL_MINUTES)
