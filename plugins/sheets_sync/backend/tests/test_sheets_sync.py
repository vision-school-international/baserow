from types import SimpleNamespace

import pytest
from sheets_sync import data_sync_types
from sheets_sync.data_sync_types import GoogleSheetsDataSyncType
from sheets_sync.sheets import (
    a1_range,
    column_letter,
    parse_spreadsheet_id,
    to_sheet_value,
)

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
    assert to_sheet_value("=IMPORTXML()") == "'=IMPORTXML()"
    assert to_sheet_value(None) == ""


class FakeClient:
    def __init__(self, values):
        self.values = values
        self.written = []

    def read_table(self):
        return self.values[0], self.values[1:]

    def update_cells(self, cells):
        self.written.extend(cells)


def _rows(monkeypatch, values, two_way):
    client = FakeClient(values)
    monkeypatch.setattr(data_sync_types, "SheetsClient", lambda instance: client)
    instance = SimpleNamespace(google_id_column="ID", two_way_sync=two_way)
    return GoogleSheetsDataSyncType().get_all_rows(instance), client


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


def test_duplicate_ids_and_missing_id_column_fail(monkeypatch):
    with pytest.raises(SyncError):
        _rows(monkeypatch, [["ID"], ["1"], ["1"]], False)
    with pytest.raises(SyncError):
        _rows(monkeypatch, [["Name"], ["Ann"]], False)
