from typing import Any
from uuid import uuid4

from django.core.cache import cache

from baserow.contrib.database.data_sync.exceptions import SyncError
from baserow.contrib.database.data_sync.registries import (
    DataSyncProperty,
    DataSyncType,
)
from baserow.contrib.database.fields.models import TextField
from baserow.core.utils import ChildProgressBuilder

from .models import GoogleSheetsDataSync, GoogleSheetsPendingRow
from .sheets import RetryableSyncError, SheetsClient, to_sheet_value
from .strategy import GoogleSheetsPushStrategy

# Far longer than one push: two requests of about 60 s each (sheets.py), whose
# limit "is not guaranteed" (google-auth max_allowed_time). Released by its owner.
PUSH_LOCK_SECONDS = 15 * 60


class PushInProgress(RetryableSyncError):
    """Another worker is writing this table's new rows to the sheet."""


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


def id_field_name(data_sync) -> str:
    return next(
        f"field_{p.field_id}"
        for p in data_sync.synced_properties.all()
        if p.unique_primary
    )


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
        # Only called on create. Imported or duplicated syncs have no user; the
        # periodic sync then runs as a workspace admin (tasks.py).
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

    def _row_numbers(self, data_sync) -> tuple[SheetsClient, list[str], dict]:
        """
        Maps every ID to its row number, read right before a write by number.
        shortcut: the Sheets API has no conditional write, so a row inserted,
        deleted or sorted in the sheet between this read and the write that follows
        it (one request later) moves the target. Upgrade to row developer metadata
        if that shows up in practice (30k characters per sheet limits it).
        """

        client, headers, rows, id_index = self._read(data_sync)
        numbers = {
            _cell(row, id_index): number
            for number, row in enumerate(rows, start=2)
            if _cell(row, id_index)
        }
        return client, headers, numbers

    def _pending_rows(self, data_sync) -> dict[int, dict]:
        """The pending rows that still exist, as {row id: {property key: value}}."""

        row_ids = list(
            GoogleSheetsPendingRow.objects.filter(data_sync=data_sync).values_list(
                "row_id", flat=True
            )
        )
        if not row_ids:
            return {}
        properties = list(data_sync.synced_properties.all())
        model = data_sync.table.get_model()
        return {
            row["id"]: {p.key: row[f"field_{p.field_id}"] for p in properties}
            for row in model.objects.filter(id__in=row_ids).values(
                "id", *[f"field_{p.field_id}" for p in properties]
            )
        }

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

    def before_sync_table(self, user, instance):
        # New Baserow rows go to the sheet before it's read, so the pull sees them.
        if not instance.two_way_sync:
            return
        try:
            self.push_pending_rows(instance)
        except PushInProgress:
            # The two-way task is pushing them; get_all_rows keeps them meanwhile.
            pass

    def get_all_rows(self, instance, progress_builder=None) -> list[dict]:
        progress = ChildProgressBuilder.build(progress_builder, child_total=2)
        # Read before the sheet: a row pushed after this read is in the sheet read.
        pending = self._pending_rows(instance) if instance.two_way_sync else {}
        client, headers, rows, id_index = self._read(instance)
        progress.increment(by=1)

        # With two-way sync on, rows added in the sheet without an ID get one, so
        # they can be synced and edited. One-way sync never writes to the sheet,
        # so those rows are left out until an ID is typed in.
        if instance.two_way_sync:
            cells = []
            for number, row in enumerate(rows, start=2):
                if _cell(row, id_index) or not any(
                    _cell(row, i) for i in range(len(row))
                ):
                    continue
                new_id = str(uuid4())
                row.extend([""] * (id_index + 1 - len(row)))
                row[id_index] = new_id
                cells.append((number, id_index, new_id))
            if cells:
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

        # Rows created in Baserow that aren't in the sheet yet are returned as they
        # are in Baserow, so core neither deletes nor changes them.
        id_key = instance.google_id_column
        for values in pending.values():
            if values.get(id_key) and values[id_key] not in seen:
                seen.add(values[id_key])
                result.append(
                    {
                        header: to_sheet_value(values.get(header))
                        for header in headers
                        if header
                    }
                )
        progress.increment(by=1)
        return result

    def push_pending_rows(self, data_sync):
        """
        Appends the pending rows that aren't in the sheet yet, with their current
        Baserow values, then marks them done. Locked per data sync, so the two-way
        task and a pull never append the same row twice.
        """

        lock_key = f"sheets_sync_push_{data_sync.id}"
        owner = str(uuid4())
        if not cache.add(lock_key, owner, timeout=PUSH_LOCK_SECONDS):
            raise PushInProgress("Another change is being written to the sheet.")
        try:
            row_ids = list(
                GoogleSheetsPendingRow.objects.filter(data_sync=data_sync).values_list(
                    "row_id", flat=True
                )
            )
            if not row_ids:
                return
            id_key = data_sync.google_id_column
            pending = self._pending_rows(data_sync)
            # The receiver always sets an ID; one that's empty anyway gets one here,
            # because core deletes rows with an empty unique primary (handler.py:684).
            missing_id = [
                row_id for row_id, values in pending.items() if not values.get(id_key)
            ]
            if missing_id:
                model = data_sync.table.get_model()
                field_name = id_field_name(data_sync)
                for row_id in missing_id:
                    new_id = str(uuid4())
                    model.objects.filter(id=row_id).update(**{field_name: new_id})
                    pending[row_id][id_key] = new_id
            client, headers, numbers = self._row_numbers(data_sync)
            new_rows = [
                [
                    to_sheet_value(values.get(header)) if header else ""
                    for header in headers
                ]
                for values in pending.values()
                if values[id_key] not in numbers
            ]
            if new_rows:
                client.append_rows(new_rows)
            # Every collected mark is done: appended, already in the sheet, or the
            # row was deleted from Baserow in the meantime.
            GoogleSheetsPendingRow.objects.filter(
                data_sync=data_sync, row_id__in=row_ids
            ).delete()
        finally:
            # Only the owner releases it, so an expired lock that another worker
            # took over is left alone. shortcut: get-then-delete isn't atomic; the
            # gap is one cache round trip after a 15 minute expiry.
            if cache.get(lock_key) == owner:
                cache.delete(lock_key)

    def create_rows(self, serialized_rows, data_sync):
        # The rows got their ID and pending mark when they were created
        # (receivers.py); no values have to be written back to Baserow.
        self.push_pending_rows(data_sync)
        return None

    def update_rows(self, serialized_rows, data_sync, updated_field_ids):
        properties = list(data_sync.synced_properties.all())
        id_field = id_field_name(data_sync)
        field_to_key = {p.field_id: p.key for p in properties if not p.unique_primary}
        changed = [
            field_id for field_id in updated_field_ids if field_id in field_to_key
        ]
        if not changed:
            return
        pending_ids = set(
            GoogleSheetsPendingRow.objects.filter(
                data_sync=data_sync, row_id__in=[row["id"] for row in serialized_rows]
            ).values_list("row_id", flat=True)
        )
        client, headers, numbers = self._row_numbers(data_sync)
        cells = []
        for row in serialized_rows:
            number = numbers.get(str(row.get(id_field) or "").strip())
            if number is None:
                if row["id"] in pending_ids:
                    # Its push may have read the values before this edit, so wait
                    # until the row is in the sheet and write the edit then.
                    raise RetryableSyncError("A new row is still being written.")
                # Deleted from the sheet in the meantime.
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
        GoogleSheetsPendingRow.objects.filter(
            data_sync=data_sync, row_id__in=[row["id"] for row in serialized_rows]
        ).delete()
        id_field = id_field_name(data_sync)
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
