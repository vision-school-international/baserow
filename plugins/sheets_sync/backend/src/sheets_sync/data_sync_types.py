from typing import Any
from uuid import uuid4

from baserow.contrib.database.data_sync.exceptions import SyncError
from baserow.contrib.database.data_sync.registries import (
    DataSyncProperty,
    DataSyncType,
)
from baserow.contrib.database.fields.models import TextField
from baserow.core.utils import ChildProgressBuilder

from .models import GoogleSheetsDataSync
from .sheets import SheetsClient, to_sheet_value
from .strategy import GoogleSheetsPushStrategy


class GoogleSheetsColumnProperty(DataSyncProperty):
    """One sheet column, keyed by its header. Cells are read as displayed text."""

    immutable_properties = True

    def to_baserow_field(self) -> TextField:
        return TextField(name=self.name)

    def is_equal(self, baserow_row_value: Any, data_sync_row_value: Any) -> bool:
        return (baserow_row_value or "") == (data_sync_row_value or "")


class GoogleSheetsIDProperty(GoogleSheetsColumnProperty):
    unique_primary = True


def _cell(row: list, index: int) -> str:
    return str(row[index]).strip() if index < len(row) else ""


class GoogleSheetsDataSyncType(DataSyncType):
    type = "google_sheets"
    model_class = GoogleSheetsDataSync
    two_way_sync_strategy_type = GoogleSheetsPushStrategy.type
    allowed_fields = [
        "google_service_account_key",
        "google_spreadsheet_id",
        "google_sheet_name",
        "google_id_column",
    ]
    request_serializer_field_names = allowed_fields
    # The key is write only, like core's `postgresql_password`.
    serializer_field_names = [
        "google_spreadsheet_id",
        "google_sheet_name",
        "google_id_column",
    ]
    sensitive_fields = ["google_service_account_key"]
    secret_field_dependencies = {
        "google_service_account_key": ["google_spreadsheet_id"],
    }

    def prepare_values(self, user, values):
        # Only called on create; the periodic sync runs on behalf of this user.
        values["authorized_user"] = user
        return values

    def _read(self, instance) -> tuple[SheetsClient, list[str], list[list], int]:
        client = SheetsClient(instance)
        headers, rows = client.read_table()
        named = [header for header in headers if header]
        duplicates = sorted({header for header in named if named.count(header) > 1})
        if duplicates:
            raise SyncError(f"Column headers must be unique: {', '.join(duplicates)}.")
        if instance.google_id_column not in headers:
            raise SyncError(
                f"The ID column '{instance.google_id_column}' is not in the header "
                "row of the sheet."
            )
        return client, headers, rows, headers.index(instance.google_id_column)

    def get_properties(self, instance) -> list[DataSyncProperty]:
        _, headers, _, _ = self._read(instance)
        return [
            (
                GoogleSheetsIDProperty
                if header == instance.google_id_column
                else GoogleSheetsColumnProperty
            )(header, header)
            for header in headers
            if header
        ]

    def get_all_rows(self, instance, progress_builder=None) -> list[dict]:
        progress = ChildProgressBuilder.build(progress_builder, child_total=2)
        client, headers, rows, id_index = self._read(instance)
        progress.increment(by=1)

        # With two-way sync on, rows added in the sheet without an ID get one, so
        # they can be synced and edited. One-way sync never writes to the sheet,
        # so those rows are left out until an ID is typed in.
        if instance.two_way_sync:
            missing = [
                (number, row)
                for number, row in enumerate(rows, start=2)
                if not _cell(row, id_index)
                and any(_cell(row, i) for i in range(len(row)))
            ]
            if missing:
                cells = []
                for number, row in missing:
                    new_id = str(uuid4())
                    row.extend([""] * (id_index + 1 - len(row)))
                    row[id_index] = new_id
                    cells.append((number, id_index, new_id))
                client.update_cells(cells)

        result, seen = [], set()
        for row in rows:
            row_id = _cell(row, id_index)
            if not row_id:
                continue
            if row_id in seen:
                raise SyncError(f"The ID '{row_id}' is used in more than one row.")
            seen.add(row_id)
            result.append(
                {
                    header: _cell(row, index)
                    for index, header in enumerate(headers)
                    if header
                }
            )
        progress.increment(by=1)
        return result

    def _row_numbers(self, data_sync) -> tuple[SheetsClient, list[str], dict]:
        client, headers, rows, id_index = self._read(data_sync)
        numbers = {
            _cell(row, id_index): number
            for number, row in enumerate(rows, start=2)
            if _cell(row, id_index)
        }
        return client, headers, numbers

    @staticmethod
    def _properties(data_sync):
        properties = list(data_sync.synced_properties.all())
        id_field = next(f"field_{p.field_id}" for p in properties if p.unique_primary)
        return properties, id_field

    def create_rows(self, serialized_rows, data_sync):
        properties, id_field = self._properties(data_sync)
        client, headers, _, _ = self._read(data_sync)
        new_rows, updates = [], []
        for row in serialized_rows:
            new_id = str(uuid4())
            values = {p.key: row.get(f"field_{p.field_id}") for p in properties}
            values[data_sync.google_id_column] = new_id
            new_rows.append(
                [
                    to_sheet_value(values.get(header)) if header else ""
                    for header in headers
                ]
            )
            # The ID is generated here, so it's written back to the Baserow row.
            updates.append({"id": row["id"], id_field: new_id})
        client.append_rows(new_rows)
        return updates

    def update_rows(self, serialized_rows, data_sync, updated_field_ids):
        properties, id_field = self._properties(data_sync)
        field_to_key = {p.field_id: p.key for p in properties if not p.unique_primary}
        changed = [
            field_id for field_id in updated_field_ids if field_id in field_to_key
        ]
        if not changed:
            return
        client, headers, numbers = self._row_numbers(data_sync)
        cells = []
        for row in serialized_rows:
            # A row deleted from the sheet in the meantime is skipped.
            number = numbers.get(str(row.get(id_field) or "").strip())
            if number is None:
                continue
            for field_id in changed:
                key = field_to_key[field_id]
                if key in headers:
                    cells.append(
                        (
                            number,
                            headers.index(key),
                            to_sheet_value(row.get(f"field_{field_id}")),
                        )
                    )
        if cells:
            client.update_cells(cells)

    def delete_rows(self, serialized_rows, data_sync):
        _, id_field = self._properties(data_sync)
        client, _, numbers = self._row_numbers(data_sync)
        row_numbers = [
            numbers[row_id]
            for row_id in (
                str(row.get(id_field) or "").strip() for row in serialized_rows
            )
            if row_id in numbers
        ]
        if row_numbers:
            client.delete_rows(row_numbers)
