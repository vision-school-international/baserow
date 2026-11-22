from unittest.mock import patch

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.shortcuts import reverse

import pytest
from flight_tracker import flight
from flight_tracker.tracker import flight_code, refresh_tracker, summary, to_cell
from rest_framework.status import HTTP_202_ACCEPTED, HTTP_400_BAD_REQUEST

from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.rows.handler import RowHandler
from baserow.contrib.database.views.handler import ViewHandler

# Shaped like the real answer for AA6 on 2026-11-22 (keys as AirLabs sent them).
AA6 = {
    "flight_iata": "AA6",
    "flight_icao": "AAL6",
    "flight_number": "6",
    "airline_iata": "AA",
    "airline_icao": "AAL",
    "airline_name": "American Airlines",
    "status": "landed",
    "dep_iata": "HNL",
    "dep_icao": "PHNL",
    "dep_name": "Daniel K. Inouye International Airport",
    "dep_city": "Honolulu",
    "dep_country": "US",
    "dep_gate": "C3",
    "dep_time": "2026-11-21 18:32",
    "dep_time_utc": "2026-11-22 04:32",
    "dep_estimated": "2026-11-21 18:22",
    "dep_actual": "2026-11-21 18:25",
    "arr_iata": "DFW",
    "arr_gate": "D23",
    "arr_baggage": "D9",
    "arr_time": "2026-11-22 06:00",
    "arr_actual": "2026-11-22 05:41",
    "arr_delayed": None,
    "duration": 448,
    "percent": 100,
    "updated": 1795322400,
    "reg_number": "N123AA",
}


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


def test_cell_shape_is_stable():
    cell = to_cell("AA6", AA6)
    assert cell["flight"] == "AA6" and cell["status"] == "landed"
    assert cell["error"] is None
    assert cell["departure"]["gate"] == "C3"
    assert cell["departure"]["actual"] == "2026-11-21 18:25"
    assert cell["arrival"]["baggage"] == "D9"
    assert cell["duration_minutes"] == 448
    assert cell["position_updated_at"].endswith("+00:00")
    # Every key is always there, null when AirLabs doesn't give it.
    empty = to_cell("AA6", {})
    assert set(empty) == set(cell)
    assert set(empty["departure"]) == set(cell["departure"])
    assert empty["departure"]["gate"] is None
    assert to_cell("AA6", {"error": "not_found"})["error"] == "not_found"


def test_summary_and_code():
    assert (
        summary(to_cell("AA6", AA6)) == "AA6 · Landed · HNL 18:25 → DFW 05:41 · Gate C3"
    )
    assert summary(to_cell("XX1", {"error": "not_found"})) == "XX1: flight not found"
    assert flight_code(" aa 6 ") == "AA6" and flight_code(None) == ""


def _tracker(data_fixture, **kwargs):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    code = data_fixture.create_text_field(table=table, name="Flight code")
    tracker = FieldHandler().create_field(
        user,
        table,
        "flight_tracker",
        name="Tracker",
        flight_code_field_id=code.id,
        **kwargs,
    )
    return user, token, table, code, tracker


@pytest.mark.django_db(transaction=True)
@patch.object(flight, "API_KEY", "key")
def test_tracker_fills_json_and_can_be_filtered(data_fixture):
    cache.clear()
    user, _, table, code, tracker = _tracker(data_fixture)
    rows = (
        RowHandler()
        .create_rows(
            user,
            table,
            [
                {f"field_{code.id}": "AA6"},
                {f"field_{code.id}": "aa 6"},
                {f"field_{code.id}": "Delta tomorrow"},
                {f"field_{code.id}": ""},
            ],
        )
        .created_rows
    )
    with patch.object(
        flight.requests, "get", return_value=FakeResponse({"response": AA6})
    ) as get:
        refresh_tracker(tracker)
    # One lookup for both AA6 rows; none for the text that isn't a flight number.
    assert get.call_count == 1
    model = table.get_model()
    cells = {r.id: getattr(r, f"field_{tracker.id}") for r in model.objects.all()}
    assert cells[rows[0].id]["status"] == "landed"
    assert cells[rows[1].id]["flight"] == "AA6"
    assert cells[rows[2].id]["error"] == "invalid_flight_number"
    assert cells[rows[3].id] is None

    # Fresh: no new lookup.
    with patch.object(flight.requests, "get") as get:
        refresh_tracker(tracker)
    assert get.call_count == 0

    view = data_fixture.create_grid_view(table=table)
    data_fixture.create_view_filter(
        view=view, field=tracker, type="flight_status", value="landed"
    )
    ids = [r.id for r in ViewHandler().get_queryset(view)]
    assert ids == [rows[0].id, rows[1].id]


@pytest.mark.django_db
def test_tracker_cells_cant_be_set(data_fixture):
    user, _, table, code, tracker = _tracker(data_fixture)
    with pytest.raises(ValidationError):
        RowHandler().create_row(
            user, table, {f"field_{tracker.id}": {"status": "landed"}}
        )


@pytest.mark.django_db
def test_tracker_settings_are_checked(data_fixture):
    user, _, table, code, tracker = _tracker(data_fixture)
    other_table = data_fixture.create_database_table(user=user)
    other = data_fixture.create_text_field(table=other_table)
    number = data_fixture.create_number_field(table=table)
    for bad in [
        {"flight_code_field_id": other.id},
        {"flight_code_field_id": number.id},
        {"flight_interval_minutes": 1},
        {"flight_refresh": "sometimes"},
    ]:
        with pytest.raises(Exception):
            FieldHandler().update_field(user, tracker, **bad)
    tracker = FieldHandler().update_field(
        user, tracker, flight_refresh="schedule", flight_interval_minutes=15
    )
    assert tracker.flight_interval_minutes == 15


@pytest.mark.django_db
def test_converting_text_to_tracker_drops_text_not_data(data_fixture):
    user, _, table, code, tracker = _tracker(data_fixture)
    notes = data_fixture.create_text_field(table=table, name="Notes")
    row = RowHandler().create_row(
        user, table, {f"field_{notes.id}": "keep me", f"field_{code.id}": "AA6"}
    )
    FieldHandler().update_field(
        user, notes, new_type_name="flight_tracker", flight_code_field_id=code.id
    )
    row.refresh_from_db()
    # The flight code field is untouched.
    assert getattr(row, f"field_{code.id}") == "AA6"


@pytest.mark.django_db
def test_refresh_endpoint(api_client, data_fixture):
    user, token, table, code, tracker = _tracker(data_fixture)
    url = reverse(
        "api:database:fields:flight_tracker:tracker_refresh",
        kwargs={"field_id": tracker.id},
    )
    with patch("flight_tracker.tasks.fill_tracker.delay") as delay:
        response = api_client.post(
            f"{url}?row_ids=1,2,2", HTTP_AUTHORIZATION=f"JWT {token}"
        )
    assert response.status_code == HTTP_202_ACCEPTED
    delay.assert_called_once_with(tracker.id, [1, 2])

    _, other_token = data_fixture.create_user_and_token()
    other = api_client.post(f"{url}?row_ids=1", HTTP_AUTHORIZATION=f"JWT {other_token}")
    assert other.status_code == HTTP_400_BAD_REQUEST
