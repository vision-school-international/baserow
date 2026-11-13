from django.conf import settings

from loguru import logger

from baserow.contrib.database.data_sync.exceptions import SyncError
from baserow.contrib.database.data_sync.registries import (
    TwoWaySyncStrategy,
    data_sync_type_registry,
)

from .sheets import RetryableSyncError

# Google's quota resets every minute (sheets/api/limits), so the first retry waits
# a minute and later ones double, up to 15 minutes.
MAX_RETRY_COUNTDOWN_SECONDS = 15 * 60


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
            push(data_sync_type_registry.get_by_model(data_sync))
        except SyncError as error:
            retries = task_context.request.retries
            # A bad key, no access or a missing column won't fix itself.
            if (
                isinstance(error, RetryableSyncError)
                and retries < settings.SHEETS_SYNC_MAX_RETRIES
            ):
                # `max_retries` overrides celery's default of 3 (Task.retry).
                raise task_context.retry(
                    countdown=min(60 * 2**retries, MAX_RETRY_COUNTDOWN_SECONDS),
                    max_retries=settings.SHEETS_SYNC_MAX_RETRIES,
                )
            logger.warning(
                "Google Sheets data sync {id}: a push failed: {error}",
                id=data_sync.id,
                error=error,
            )
            # New rows stay pending: every pull tries them again and keeps them
            # until then (data_sync_types.py).
            data_sync.last_error = (
                f"A change could not be written to the sheet: {error}"
            )
            data_sync.save(update_fields=("last_error",))

    def rows_created(self, task_context, serialized_rows, data_sync):
        self._push(
            task_context,
            data_sync,
            lambda sync_type: sync_type.create_rows(serialized_rows, data_sync),
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
