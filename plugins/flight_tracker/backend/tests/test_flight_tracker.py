from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.shortcuts import reverse
from django.test import override_settings
from django.utils import timezone

import pytest
from flight_tracker import flight
from flight_tracker.flight import FlightLookupError, clean_flight, lookup, refresh
from flight_tracker.models import FlightStatus
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.rows.handler import RowHandler

AA6 = {"flight_iata": "AA6", "status": "en-route", "dep_iata": "OGG", "hex": "AAB812"}


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


def test_clean_flight():
    assert clean_flight(" aa 6 ") == "AA6"
    assert clean_flight("aal6") == "AAL6"
    assert clean_flight("u21234") == "U21234"
    assert clean_flight("") == ""
    assert clean_flight(None) is None
    for bad in ["A6", "AA", "AA12345", "AAAA6", "AA6!", "AA-6"]:
        with pytest.raises(ValidationError):
            clean_flight(bad)


@patch.object(flight, "API_KEY", "key")
def test_lookup_reads_the_answer_and_errors():
    with patch.object(flight.requests, "get", return_value=FakeResponse(AA6)) as get:
        # The whole answer: the tracker keeps more than the flight field.
        assert lookup("AA6") == AA6
    assert get.call_args.kwargs["params"] == {"flight_iata": "AA6", "api_key": "key"}

    with patch.object(
        flight.requests, "get", return_value=FakeResponse({"response": AA6})
    ) as get:
        assert lookup("AAL6")["status"] == "en-route"
    assert "flight_icao" in get.call_args.kwargs["params"]

    not_found = {"error": {"message": "Not found", "code": "not_found"}}
    with patch.object(flight.requests, "get", return_value=FakeResponse(not_found)):
        assert lookup("AA6") == {"error": "not_found"}

    limit = {"error": {"message": "Limit", "code": "month_limit_exceeded"}}
    with patch.object(flight.requests, "get", return_value=FakeResponse(limit)):
        with pytest.raises(FlightLookupError) as exc:
            lookup("AA6")
    assert exc.value.code == "month_limit_exceeded"


@patch.object(flight, "API_KEY", "key")
@override_settings(FLIGHT_TRACKER_MAX_LOOKUPS_PER_DAY=2)
def test_lookups_stop_at_the_daily_limit():
    cache.clear()
    with patch.object(flight.requests, "get", return_value=FakeResponse(AA6)) as get:
        lookup("AA6")
        lookup("AA6")
        with pytest.raises(FlightLookupError) as exc:
            lookup("AA6")
    assert exc.value.code == "local_day_limit" and get.call_count == 2


@patch.object(flight, "API_KEY", "")
def test_lookup_without_a_key():
    with pytest.raises(FlightLookupError):
        lookup("AA6")


def _setup(data_fixture, refresh_mode="view"):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user, table, "flight", name="Flight", flight_refresh=refresh_mode
    )
    return user, token, table, field


@pytest.mark.django_db
def test_cells_are_cleaned_and_checked(data_fixture):
    user, _, table, field = _setup(data_fixture)
    row = RowHandler().create_row(user, table, {f"field_{field.id}": "aa 6"})
    assert getattr(row, f"field_{field.id}") == "AA6"
    with pytest.raises(ValidationError):
        RowHandler().create_row(user, table, {f"field_{field.id}": "nope!"})


@pytest.mark.django_db
@patch.object(flight, "API_KEY", "key")
def test_refresh_looks_each_flight_up_once_and_keeps_good_data(data_fixture):
    _, _, _, field = _setup(data_fixture)
    with patch.object(flight.requests, "get", return_value=FakeResponse(AA6)) as get:
        statuses, error = refresh(
            field, {1: "AA6", 2: "AA6", 3: "", 4: "Delta tomorrow, seat 12"}
        )
    assert get.call_count == 1 and error is None
    assert set(statuses) == {1, 2} and statuses[1]["status"] == "en-route"
    # The flight field keeps only KEPT_FIELDS, not e.g. the aircraft hex.
    assert "hex" not in statuses[1]

    # Fresh: no lookup. Stale with max_age: looked up, and a failure keeps the data.
    with patch.object(flight.requests, "get") as get:
        refresh(field, {1: "AA6"}, max_age=timedelta(minutes=5))
    assert get.call_count == 0
    FlightStatus.objects.update(fetched_at=timezone.now() - timedelta(hours=1))
    limit = {"error": {"code": "minute_limit_exceeded"}}
    with patch.object(flight.requests, "get", return_value=FakeResponse(limit)):
        statuses, error = refresh(field, {1: "AA6"}, max_age=timedelta(minutes=5))
    assert error == "minute_limit_exceeded"
    assert statuses[1]["status"] == "en-route"

    # A changed cell doesn't show the old flight's status.
    with patch.object(flight.requests, "get", return_value=FakeResponse(limit)):
        statuses, _ = refresh(field, {1: "BA1"})
    assert statuses == {}


@pytest.mark.django_db
@patch.object(flight, "API_KEY", "key")
def test_status_endpoint(api_client, data_fixture):
    user, token, table, field = _setup(data_fixture)
    row = RowHandler().create_row(user, table, {f"field_{field.id}": "AA6"})
    url = reverse(
        "api:database:fields:flight_tracker:status", kwargs={"field_id": field.id}
    )

    with patch.object(flight.requests, "get", return_value=FakeResponse(AA6)):
        response = api_client.get(
            f"{url}?row_ids={row.id}", HTTP_AUTHORIZATION=f"JWT {token}"
        )
    assert response.status_code == HTTP_200_OK
    assert response.json()["statuses"][str(row.id)]["status"] == "en-route"

    bad = api_client.get(f"{url}?row_ids=1;2", HTTP_AUTHORIZATION=f"JWT {token}")
    assert bad.status_code == HTTP_400_BAD_REQUEST

    # Someone outside the workspace gets nothing.
    _, other_token = data_fixture.create_user_and_token()
    other = api_client.get(
        f"{url}?row_ids={row.id}", HTTP_AUTHORIZATION=f"JWT {other_token}"
    )
    assert other.status_code == HTTP_400_BAD_REQUEST
    assert other.json()["error"] == "ERROR_USER_NOT_IN_GROUP"

    text_field = data_fixture.create_text_field(table=table)
    url = reverse(
        "api:database:fields:flight_tracker:status", kwargs={"field_id": text_field.id}
    )
    missing = api_client.get(
        f"{url}?row_ids={row.id}", HTTP_AUTHORIZATION=f"JWT {token}"
    )
    assert missing.status_code == HTTP_404_NOT_FOUND
