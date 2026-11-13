from uuid import uuid4

from django.dispatch import receiver

from baserow.contrib.database.rows.signals import rows_created

from .models import GoogleSheetsDataSync, GoogleSheetsPendingRow


@receiver(rows_created)
def give_new_rows_a_sheet_id(
    sender, rows, table, model, skip_two_way_sync=False, **kwargs
):
    """
    Gives a row created in a two-way synced table its sheet ID and a pending mark
    in the transaction that creates it. Without them, a pull that runs before the
    row reaches the sheet would delete it: core deletes rows with an empty unique
    primary and rows missing from the source (data_sync/handler.py:676-685).

    The ID is set on the row objects too: the API response and the realtime event
    serialize them when the transaction commits (ws/rows/signals.py:69-75).
    """

    # Rows the sync itself creates come from the sheet and already have an ID.
    if skip_two_way_sync or not table.is_two_way_data_synced_table:
        return
    data_sync = table.data_sync.specific
    if not isinstance(data_sync, GoogleSheetsDataSync):
        return

    from .data_sync_types import id_field_name

    id_field = id_field_name(data_sync)
    for row in rows:
        if not getattr(row, id_field):
            setattr(row, id_field, str(uuid4()))
    # shortcut: written past RowHandler, so the search index has the ID only after
    # the row's next update; fine while nobody searches by sheet ID.
    model.objects.bulk_update(rows, [id_field])
    GoogleSheetsPendingRow.objects.bulk_create(
        [GoogleSheetsPendingRow(data_sync=data_sync, row_id=row.id) for row in rows],
        ignore_conflicts=True,
    )
