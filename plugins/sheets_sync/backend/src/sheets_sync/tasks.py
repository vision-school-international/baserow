from datetime import timedelta
from itertools import chain

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
    from baserow.contrib.database.data_sync.operations import SyncTableOperationType
    from baserow.core.handler import CoreHandler
    from baserow.core.jobs.exceptions import MaxJobCountExceeded
    from baserow.core.jobs.handler import JobHandler
    from baserow.core.models import WORKSPACE_USER_PERMISSION_ADMIN, WorkspaceUser

    from .models import GoogleSheetsDataSync

    data_sync = (
        GoogleSheetsDataSync.objects.select_related(
            "authorized_user", "table__database__workspace"
        )
        .filter(id=data_sync_id)
        .first()
    )
    if data_sync is None:
        return

    # The creator, else a workspace admin: imported or duplicated syncs have no
    # creator (prepare_values only runs on create), and a creator can be removed
    # from the workspace. Each candidate gets the same check the sync job makes
    # (data_sync/job_types.py:288), without raising.
    workspace = data_sync.table.database.workspace
    admins = (
        WorkspaceUser.objects.filter(
            workspace=workspace,
            permissions=WORKSPACE_USER_PERMISSION_ADMIN,
            user__is_active=True,
        )
        .select_related("user")
        .order_by("id")
    )
    # Lazy: the admins are only queried, a row at a time, if the creator fails.
    candidates = chain(
        [data_sync.authorized_user], (admin.user for admin in admins.iterator())
    )
    core_handler = CoreHandler()
    user = next(
        (
            candidate
            for candidate in candidates
            if candidate is not None
            and candidate.is_active
            and core_handler.check_permissions(
                candidate,
                SyncTableOperationType.type,
                workspace=workspace,
                context=data_sync.table,
                raise_permission_exceptions=False,
            )
        ),
        None,
    )
    if user is None:
        message = "The periodic sync has no workspace member to run as."
        logger.warning("Google Sheets data sync {id}: {m}", id=data_sync_id, m=message)
        # Saved once, not on every tick; a successful sync clears it
        # (data_sync/handler.py:752).
        if data_sync.last_error != message:
            data_sync.last_error = message
            data_sync.save(update_fields=("last_error",))
        return

    try:
        JobHandler().create_and_start_job(
            user,
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
        table__trashed=False,
        table__database__trashed=False,
        table__database__workspace__trashed=False,
    ).values_list("id", flat=True)
    for data_sync_id in data_sync_ids:
        sync_google_sheet.delay(data_sync_id)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        timedelta(minutes=settings.SHEETS_SYNC_INTERVAL_MINUTES),
        sync_all_google_sheets.s(),
    )
