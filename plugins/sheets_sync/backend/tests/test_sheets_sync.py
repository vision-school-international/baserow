from types import SimpleNamespace

import pytest
from celery.exceptions import Retry
from sheets_sync import data_sync_types
from sheets_sync.data_sync_types import GoogleSheetsDataSyncType
from sheets_sync.sheets import (
    RetryableSyncError,
    a1_range,
    column_letter,
    parse_spreadsheet_id,
    to_sheet_value,
)
from sheets_sync.strategy import GoogleSheetsPushStrategy

from baserow.contrib.database.data_sync.exceptions import SyncError


def test_helpers():
    assert [column_letter(i) for i in (0, 25, 26, 701, 702)] == [
        "A",
        "Z",
        "AA",
        "ZZ",
        "AAA",
    ]
    assert (
        parse_spreadsheet_id("https://docs.google.com/spreadsheets/d/abc_-1/edit#gid=0")
        == "abc_-1"
    )
    assert parse_spreadsheet_id(" abc ") == "abc"
    assert a1_range("My Sheet", "B2") == "'My Sheet'!B2"
    # Written RAW, so values go through unchanged.
    assert to_sheet_value("=IMPORTXML()") == "=IMPORTXML()"
    assert to_sheet_value("007") == "007"
    assert to_sheet_value(None) == ""


class FakeClient:
    def __init__(self, values):
        self.values = values
        self.written = []
        self.appended = []

    def read_table(self):
        return self.values[0], self.values[1:]

    def update_cells(self, cells):
        self.written.extend(cells)

    def append_rows(self, rows):
        self.appended.extend(rows)


def _rows(monkeypatch, values, two_way, pending=None):
    client = FakeClient(values)
    monkeypatch.setattr(data_sync_types, "SheetsClient", lambda instance: client)
    sync_type = GoogleSheetsDataSyncType()
    monkeypatch.setattr(sync_type, "_pending_rows", lambda instance: pending or {})
    instance = SimpleNamespace(google_id_column="ID", two_way_sync=two_way)
    return sync_type.get_all_rows(instance), client


def test_one_way_skips_rows_without_id(monkeypatch):
    rows, client = _rows(
        monkeypatch, [["ID", "Name", ""], ["1", "Ann", "x"], ["", "Bob"]], False
    )
    assert rows == [{"ID": "1", "Name": "Ann"}]
    assert client.written == []


def test_two_way_gives_new_rows_an_id(monkeypatch):
    rows, client = _rows(monkeypatch, [["ID", "Name"], ["", "Bob"], []], True)
    assert len(client.written) == 1
    number, column, new_id = client.written[0]
    assert (number, column) == (2, 0)
    assert rows == [{"ID": new_id, "Name": "Bob"}]


def test_pending_rows_are_kept_until_they_are_in_the_sheet(monkeypatch):
    pending = {
        7: {"ID": "new", "Name": "Cy"},
        8: {"ID": "1", "Name": "stale"},
    }
    rows, _ = _rows(monkeypatch, [["ID", "Name"], ["1", "Ann"]], True, pending)
    # The pending row that's already in the sheet comes from the sheet.
    assert rows == [{"ID": "1", "Name": "Ann"}, {"ID": "new", "Name": "Cy"}]


def test_duplicate_ids_and_missing_id_column_fail(monkeypatch):
    with pytest.raises(SyncError):
        _rows(monkeypatch, [["ID"], ["1"], ["1"]], False)
    with pytest.raises(SyncError):
        _rows(monkeypatch, [["Name"], ["Ann"]], False)


class FakeTask:
    def __init__(self, retries):
        self.request = SimpleNamespace(retries=retries)
        self.countdown = None

    def retry(self, countdown, max_retries):
        self.countdown = countdown
        return Retry()


class FakeDataSync:
    id = 1
    last_error = None

    def save(self, update_fields):
        self.saved = update_fields


def _push(monkeypatch, error, retries):
    sync_type = SimpleNamespace(update_rows=lambda *args: (_ for _ in ()).throw(error))
    monkeypatch.setattr(
        "sheets_sync.strategy.data_sync_type_registry.get_by_model",
        lambda data_sync: sync_type,
    )
    task, data_sync = FakeTask(retries), FakeDataSync()
    GoogleSheetsPushStrategy().rows_updated(task, [], data_sync, [1])
    return task, data_sync


def test_only_retryable_errors_are_retried(monkeypatch, settings):
    settings.SHEETS_SYNC_MAX_RETRIES = 5
    with pytest.raises(Retry):
        _push(monkeypatch, RetryableSyncError("429"), 2)

    task, data_sync = _push(monkeypatch, SyncError("403"), 0)
    assert task.countdown is None
    assert "403" in data_sync.last_error

    task, data_sync = _push(monkeypatch, RetryableSyncError("429"), 5)
    assert "429" in data_sync.last_error


def test_retry_waits_at_least_a_minute(monkeypatch, settings):
    settings.SHEETS_SYNC_MAX_RETRIES = 5
    task = FakeTask(0)
    sync_type = SimpleNamespace(
        update_rows=lambda *args: (_ for _ in ()).throw(RetryableSyncError("429"))
    )
    monkeypatch.setattr(
        "sheets_sync.strategy.data_sync_type_registry.get_by_model",
        lambda data_sync: sync_type,
    )
    with pytest.raises(Retry):
        GoogleSheetsPushStrategy().rows_updated(task, [], FakeDataSync(), [1])
    assert task.countdown == 60
