"""
Two-way flow against a fake sheet: the receiver, the pending marks, pushes and
the periodic run-as user. Patterned on core's data sync tests
(tests/baserow/contrib/database/data_sync/test_data_sync_ical_calendar_type.py).
"""

import pytest
from sheets_sync import data_sync_types, tasks
from sheets_sync.models import GoogleSheetsPendingRow

from baserow.contrib.database.data_sync.exceptions import SyncError
from baserow.contrib.database.data_sync.handler import DataSyncHandler
from baserow.contrib.database.rows.handler import RowHandler


class FakeSheet:
    def __init__(self, values):
        self.values = values
        self.fail_writes = False

    def read_table(self):
        return list(self.values[0]), [list(row) for row in self.values[1:]]

    def _write(self):
        if self.fail_writes:
            raise SyncError("Google Sheets responded with 403: no access")

    def append_rows(self, rows):
        self._write()
        self.values.extend(rows)

    def update_cells(self, cells):
        self._write()
        for number, column, value in cells:
            row = self.values[number - 1]
            row.extend([""] * (column + 1 - len(row)))
            row[column] = value

    def delete_rows(self, numbers):
        self._write()
        for number in sorted(numbers, reverse=True):
            del self.values[number - 1]


@pytest.fixture
def sheet(monkeypatch):
    fake = FakeSheet([["ID", "Name"], ["1", "Ann"]])
    monkeypatch.setattr(data_sync_types, "SheetsClient", lambda instance: fake)
    return fake


def _create(data_fixture, two_way=True):
    user = data_fixture.create_user()
    database = data_fixture.create_database_application(user=user)
    handler = DataSyncHandler()
    data_sync = handler.create_data_sync_table(
        user=user,
        database=database,
        table_name="Sheet",
        type_name="google_sheets",
        synced_properties=["ID", "Name"],
        two_way_sync=two_way,
        google_service_account_key="{}",
        google_spreadsheet_id="sheet-id",
        google_sheet_name="Sheet1",
        google_id_column="ID",
    )
    handler.sync_data_sync_table(user=user, data_sync=data_sync)
    fields = {p.key: p.field for p in data_sync.synced_properties.all()}
    return user, data_sync, fields


def _rows(data_sync, fields):
    model = data_sync.table.get_model()
    return {
        getattr(row, f"field_{fields['ID'].id}"): getattr(
            row, f"field_{fields['Name'].id}"
        )
        for row in model.objects.all()
    }


@pytest.mark.django_db(transaction=True)
def test_new_row_gets_an_id_and_reaches_the_sheet_on_the_next_sync(data_fixture, sheet):
    user, data_sync, fields = _create(data_fixture)

    row = RowHandler().create_row(
        user, data_sync.table, {f"field_{fields['Name'].id}": "Cy"}
    )
    new_id = getattr(row, f"field_{fields['ID'].id}")
    assert new_id
    assert GoogleSheetsPendingRow.objects.filter(row_id=row.id).exists()

    DataSyncHandler().sync_data_sync_table(user=user, data_sync=data_sync)

    assert [new_id, "Cy"] in sheet.values
    assert not GoogleSheetsPendingRow.objects.exists()
    assert _rows(data_sync, fields) == {"1": "Ann", new_id: "Cy"}


@pytest.mark.django_db(transaction=True)
def test_a_row_that_cannot_be_written_is_kept(data_fixture, sheet):
    user, data_sync, fields = _create(data_fixture)
    row = RowHandler().create_row(
        user, data_sync.table, {f"field_{fields['Name'].id}": "Cy"}
    )
    sheet.fail_writes = True

    data_sync = DataSyncHandler().sync_data_sync_table(user=user, data_sync=data_sync)

    assert "403" in data_sync.last_error
    assert GoogleSheetsPendingRow.objects.filter(row_id=row.id).exists()
    assert "Cy" in _rows(data_sync, fields).values()


@pytest.mark.django_db(transaction=True)
def test_pushes_update_and_delete_the_right_row(data_fixture, sheet):
    user, data_sync, fields = _create(data_fixture)
    sync_type = data_sync_types.GoogleSheetsDataSyncType()
    id_name, name_name = f"field_{fields['ID'].id}", f"field_{fields['Name'].id}"

    sync_type.update_rows(
        [{"id": 1, id_name: "1", name_name: "Anna"}], data_sync, [fields["Name"].id]
    )
    assert sheet.values[1] == ["1", "Anna"]

    sync_type.delete_rows([{"id": 1, id_name: "1"}], data_sync)
    assert sheet.values == [["ID", "Name"]]


@pytest.mark.django_db(transaction=True)
def test_an_edit_waits_for_a_pending_row(data_fixture, sheet):
    user, data_sync, fields = _create(data_fixture)
    row = RowHandler().create_row(
        user, data_sync.table, {f"field_{fields['Name'].id}": "Cy"}
    )
    id_name, name_name = f"field_{fields['ID'].id}", f"field_{fields['Name'].id}"

    with pytest.raises(data_sync_types.RetryableSyncError):
        data_sync_types.GoogleSheetsDataSyncType().update_rows(
            [{"id": row.id, id_name: getattr(row, id_name), name_name: "Cyd"}],
            data_sync,
            [fields["Name"].id],
        )


@pytest.mark.django_db(transaction=True)
def test_periodic_sync_runs_as_an_admin_when_the_creator_left(
    data_fixture, sheet, monkeypatch
):
    user, data_sync, _ = _create(data_fixture)
    workspace = data_sync.table.database.workspace
    admin = data_fixture.create_user()
    data_fixture.create_user_workspace(
        user=admin, workspace=workspace, permissions="ADMIN"
    )
    workspace.workspaceuser_set.filter(user=user).delete()

    ran_as = []
    monkeypatch.setattr(
        "baserow.core.jobs.handler.JobHandler.create_and_start_job",
        lambda self, run_user, *args, **kwargs: ran_as.append(run_user),
    )
    tasks.sync_google_sheet(data_sync.id)

    assert ran_as == [admin]
