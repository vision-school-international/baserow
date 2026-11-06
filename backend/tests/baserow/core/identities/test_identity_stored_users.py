import pytest

from baserow.contrib.database.table.models import DuplicateTableJob, Table
from baserow.core.cache import local_cache
from baserow.core.exceptions import PermissionException
from baserow.core.jobs.tasks import run_async_job
from baserow.core.models import WorkspaceUser


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("revocation", ["trash", "disable", "membership", "role"])
def test_queued_identity_job_rechecks_current_authority(data_fixture, revocation):
    table = data_fixture.create_database_table()
    identity = data_fixture.create_identity(workspace=table.database.workspace)
    job = DuplicateTableJob.objects.create(user=identity, original_table=table)
    if revocation == "trash":
        identity.profile.trashed = True
        identity.profile.save(update_fields=["trashed"])
    elif revocation == "disable":
        identity.is_active = False
        identity.save(update_fields=["is_active"])
    elif revocation == "membership":
        WorkspaceUser.objects_and_trash.filter(user=identity).delete()
    else:
        WorkspaceUser.objects_and_trash.filter(user=identity).update(
            permissions="NO_ACCESS"
        )

    with local_cache.context(), pytest.raises(PermissionException):
        run_async_job(job.id)

    job.refresh_from_db()
    assert job.failed
    assert job.duplicated_table_id is None
    assert Table.objects.count() == 1
