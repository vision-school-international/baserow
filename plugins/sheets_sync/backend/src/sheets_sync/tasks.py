from datetime import timedelta

from django.conf import settings

from loguru import logger

from baserow.config.celery import app


@app.task(queue="export")
def sync_google_sheet(data_sync_id: int):
    """
    Runs the core sync job as the user who created the sync, so the run shows in
    the sync history. Same shape as the enterprise periodic sync
    (baserow_enterprise/data_sync/handler.py:186-240), which is not loaded.
    """

    from baserow.contrib.database.data_sync.job_types import SyncDataSyncTableJobType
    from baserow.contrib.database.data_sync.models import (
        DATA_SYNC_JOB_TRIGGERED_BY_PERIODIC,
    )
    from baserow.core.jobs.exceptions import MaxJobCountExceeded
    from baserow.core.jobs.handler import JobHandler

    from .models import GoogleSheetsDataSync

    data_sync = (
        GoogleSheetsDataSync.objects.select_related("authorized_user")
        .filter(id=data_sync_id)
        .first()
    )
    if data_sync is None or data_sync.authorized_user is None:
        return

    try:
        JobHandler().create_and_start_job(
            data_sync.authorized_user,
            SyncDataSyncTableJobType.type,
            sync=True,
            data_sync_id=data_sync_id,
            triggered_by=DATA_SYNC_JOB_TRIGGERED_BY_PERIODIC,
        )
    except MaxJobCountExceeded:
        logger.info(
            "Google Sheets data sync {id} skipped: a sync is already running.",
            id=data_sync_id,
        )
    except Exception:
        logger.exception("Google Sheets data sync {id} failed.", id=data_sync_id)


@app.task(queue="export")
def sync_all_google_sheets():
    from .models import GoogleSheetsDataSync

    data_sync_ids = GoogleSheetsDataSync.objects.filter(
        authorized_user__is_active=True,
        table__trashed=False,
        table__database__trashed=False,
    ).values_list("id", flat=True)
    for data_sync_id in data_sync_ids:
        sync_google_sheet.delay(data_sync_id)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        timedelta(minutes=settings.SHEETS_SYNC_INTERVAL_MINUTES),
        sync_all_google_sheets.s(),
    )
