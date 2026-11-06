import pytest

from baserow.contrib.database.table.actions import CreateTableActionType
from baserow.contrib.database.tools.fields import FieldItemCreate
from baserow.contrib.database.tools.tables import TableItemCreate, create_tables
from baserow.core.action.models import Action
from baserow.core.action.signals import action_done
from baserow.core.exceptions import PermissionException
from baserow.core.tools import ToolContext
from baserow.core.tools.applications import list_applications


@pytest.mark.django_db
def test_identity_tools_use_shared_actions_without_interactive_undo(
    data_fixture, mocker
):
    database = data_fixture.create_database_application()
    identity = data_fixture.create_identity(workspace=database.workspace)
    ctx = ToolContext(user=identity, workspace=database.workspace)
    send_action = mocker.spy(action_done, "send")

    applications = list_applications(ctx)
    result = create_tables(
        ctx,
        database.id,
        [
            TableItemCreate(
                name="Tasks",
                primary_field_name="Task",
                fields=[FieldItemCreate(name="Notes", type="text")],
            )
        ],
    )

    table = database.table_set.get(name="Tasks")
    assert [app["id"] for app in applications["applications"]] == [database.id]
    assert result["created_tables"][0]["id"] == table.id
    assert set(table.field_set.values_list("name", flat=True)) == {"Task", "Notes"}
    assert not Action.objects.filter(user=identity).exists()
    assert any(
        call.kwargs["sender"] is CreateTableActionType
        and call.kwargs["user"] == identity
        for call in send_action.call_args_list
    )


@pytest.mark.django_db
@pytest.mark.parametrize("denial", ["disabled", "trashed", "other_workspace"])
def test_identity_tools_recheck_execution_permissions(data_fixture, denial):
    database = data_fixture.create_database_application()
    identity = data_fixture.create_identity(
        workspace=(
            data_fixture.create_workspace()
            if denial == "other_workspace"
            else database.workspace
        ),
        is_active=denial != "disabled",
        trashed=denial == "trashed",
    )
    ctx = ToolContext(user=identity, workspace=database.workspace)

    with pytest.raises(PermissionException):
        create_tables(
            ctx,
            database.id,
            [TableItemCreate(name="Tasks", primary_field_name="Task", fields=[])],
        )

    assert not database.table_set.exists()
    assert not Action.objects.filter(user=identity).exists()
