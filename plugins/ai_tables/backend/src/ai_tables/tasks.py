from datetime import datetime, timedelta, timezone
from typing import List

from django.conf import settings
from django.db import transaction

from celery_singleton import DuplicateTaskError, Singleton

from baserow.celery_singleton_backend import SingletonAutoRescheduleFlag
from baserow.config.celery import app

PERIODIC_CHECK_MINUTES = 5


def _reschedule_flag(field_id: int) -> SingletonAutoRescheduleFlag:
    return SingletonAutoRescheduleFlag(f"ai_tables_auto_update_{field_id}")


def _start_auto_update_task(field_id: int):
    try:
        run_auto_update.s(field_id=field_id).apply_async(
            countdown=settings.AI_TABLES_AUTO_UPDATE_DEBOUNCE_SECONDS
        )
    except DuplicateTaskError:
        # A run is queued or running: it reschedules itself when done.
        _reschedule_flag(field_id).set()


def schedule_auto_update(field_id: int, row_ids: List[int]):
    """
    Records the rows to regenerate in the same transaction as the change that
    caused it, and starts the debounced task once that transaction commits.
    """

    from .models import AIPromptScheduledUpdate

    now = datetime.now(tz=timezone.utc)
    AIPromptScheduledUpdate.objects.bulk_create(
        [
            AIPromptScheduledUpdate(field_id=field_id, row_id=row_id, updated_on=now)
            for row_id in row_ids
        ],
        update_conflicts=True,
        unique_fields=["field", "row_id"],
        update_fields=["updated_on"],
        batch_size=1000,
    )
    transaction.on_commit(lambda: _start_auto_update_task(field_id))


@app.task(
    queue="export",
    base=Singleton,
    unique_on="field_id",
    raise_on_duplicate=True,
    lock_expiry=settings.CELERY_SEARCH_UPDATE_HARD_TIME_LIMIT,
    soft_time_limit=settings.CELERY_SEARCH_UPDATE_HARD_TIME_LIMIT,
    time_limit=settings.CELERY_SEARCH_UPDATE_HARD_TIME_LIMIT,
)
def run_auto_update(field_id: int):
    """
    One run per field at a time. Rows changed again while generating keep their
    entry (newer `updated_on`) and are picked up by the rescheduled run.
    """

    from .handler import AIPromptHandler
    from .models import AIPromptScheduledUpdate

    flag = _reschedule_flag(field_id)
    flag.clear()
    started = datetime.now(tz=timezone.utc)
    scheduled = AIPromptScheduledUpdate.objects.filter(field_id=field_id)
    row_ids = list(scheduled.values_list("row_id", flat=True))
    if row_ids:
        AIPromptHandler().run_auto_update(field_id, row_ids)
        scheduled.filter(row_id__in=row_ids, updated_on__lte=started).delete()
    if flag.is_set():
        _start_auto_update_task(field_id)


@app.task(
    queue="export",
    base=Singleton,
    raise_on_duplicate=False,
    soft_time_limit=PERIODIC_CHECK_MINUTES * 60,
    time_limit=PERIODIC_CHECK_MINUTES * 60,
    lock_expiry=PERIODIC_CHECK_MINUTES * 60,
)
def reschedule_pending_auto_updates():
    """
    Drops entries of fields that no longer auto-update, and restarts fields whose
    run was lost (e.g. a worker restart).
    """

    from .models import AI_PROMPT_FIELD_MODELS, AIPromptScheduledUpdate

    active = set()
    for model in AI_PROMPT_FIELD_MODELS:
        active.update(
            model.objects.filter(
                ai_auto_update=True, ai_auto_update_user__isnull=False
            ).values_list("id", flat=True)
        )
    AIPromptScheduledUpdate.objects.exclude(field_id__in=active).delete()
    for field_id in (
        AIPromptScheduledUpdate.objects.order_by()
        .values_list("field_id", flat=True)
        .distinct()
    ):
        _start_auto_update_task(field_id)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        timedelta(minutes=PERIODIC_CHECK_MINUTES),
        reschedule_pending_auto_updates.s(),
    )
