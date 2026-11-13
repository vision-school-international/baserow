from django.conf import settings
from django.db import transaction

from loguru import logger

from baserow.contrib.database.data_sync.exceptions import SyncError
from baserow.contrib.database.data_sync.registries import (
    TwoWaySyncStrategy,
    data_sync_type_registry,
)
from baserow.contrib.database.rows.handler import RowHandler


class GoogleSheetsPushStrategy(TwoWaySyncStrategy):
    """
    Pushes every Baserow change to the sheet right away. Sheet changes come in
    with the periodic or manual sync. Our own, because the enterprise
    `realtime_push` strategy is not loaded.

    `data_sync` is already specific: data_sync/tasks.py gets it through
    DataSyncHandler.get_data_sync, which returns `.specific`.
    """

    type = "google_sheets_push"

    def before_enable(self, workspace):
        # Core calls it with the workspace (data_sync/handler.py:186, :307).
        pass

    def _push(self, task_context, data_sync, push):
        try:
            return push(data_sync_type_registry.get_by_model(data_sync))
        except SyncError as error:
            retries = task_context.request.retries
            if retries < settings.SHEETS_SYNC_MAX_RETRIES:
                # Exponential backoff, as Google asks for on 429 (sheets/api/limits).
                # `max_retries` overrides celery's default of 3 (Task.retry).
                raise task_context.retry(
                    countdown=2**retries, max_retries=settings.SHEETS_SYNC_MAX_RETRIES
                )
            logger.warning(
                "Google Sheets data sync {id}: a push failed: {error}",
                id=data_sync.id,
                error=error,
            )
            data_sync.last_error = (
                f"A change could not be written to the sheet: {error}"
            )
            data_sync.save(update_fields=("last_error",))
            return None

    def rows_created(self, task_context, serialized_rows, data_sync):
        rows_to_update = self._push(
            task_context,
            data_sync,
            lambda sync_type: sync_type.create_rows(serialized_rows, data_sync),
        )
        if not rows_to_update:
            return
        # Writes the generated IDs back; skip_two_way_sync stops it echoing back
        # to the sheet (data_sync/receivers.py).
        with transaction.atomic():
            RowHandler().force_update_rows(
                user=None,
                table=data_sync.table,
                rows_values=rows_to_update,
                signal_params={"skip_two_way_sync": True},
            )

    def rows_updated(self, task_context, serialized_rows, data_sync, updated_field_ids):
        self._push(
            task_context,
            data_sync,
            lambda sync_type: sync_type.update_rows(
                serialized_rows, data_sync, updated_field_ids
            ),
        )

    def rows_deleted(self, task_context, serialized_rows, data_sync):
        self._push(
            task_context,
            data_sync,
            lambda sync_type: sync_type.delete_rows(serialized_rows, data_sync),
        )
