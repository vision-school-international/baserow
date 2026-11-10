import contextlib

from django.db import transaction

import pytest

from baserow.contrib.agent.chat_run_type import AgentChatRunType
from baserow.contrib.agent.exceptions import AgentConversationReadOnly
from baserow.contrib.agent.handler import AgentHandler
from baserow.contrib.agent.models import AgentConversation
from baserow.contrib.agent.service import AgentService
from baserow.core.chat_runs.models import ChatRun
from baserow.core.exceptions import PermissionException
from baserow.core.trash.handler import TrashHandler
from baserow_enterprise.role.handler import RoleAssignmentHandler
from baserow_enterprise.role.models import Role

READ = {"list", "read", "follow"}
CHANGE = READ | {"stop", "rename", "delete"}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role_uid,allowed,send_error",
    [
        (None, set(), PermissionException),
        ("NO_ACCESS", set(), PermissionException),
        ("VIEWER", READ, PermissionException),
        ("EDITOR", READ, AgentConversationReadOnly),
        ("BUILDER", CHANGE, AgentConversationReadOnly),
        ("ADMIN", CHANGE, AgentConversationReadOnly),
    ],
    ids=["non-member", "no-access", "viewer", "editor", "builder", "admin"],
)
def test_shared_conversations_are_read_by_every_role_and_changed_by_builders(
    enterprise_data_fixture,
    enable_enterprise,
    synced_roles,
    role_uid,
    allowed,
    send_error,
):
    """Viewers and editors watch; builders rename, trash and stop; nobody sends."""

    admin = enterprise_data_fixture.create_user()
    user = enterprise_data_fixture.create_user()
    workspace = enterprise_data_fixture.create_workspace(
        user=admin, members=[user] if role_uid else []
    )
    if role_uid:
        RoleAssignmentHandler().assign_role(
            user, workspace, Role.objects.get(uid=role_uid)
        )
    agent = enterprise_data_fixture.create_agent_application(workspace=workspace)
    trigger = enterprise_data_fixture.create_agent_trigger(agent=agent)
    conversation = AgentHandler().start_trigger_conversation(trigger, "Tick")
    run = ChatRun.objects.get(run_type="agent", chat_id=conversation.id)
    service, run_type = AgentService(), AgentChatRunType()
    attempts = {
        "list": lambda: (
            conversation.uuid
            in {item.uuid for item in service.list_conversations(user, agent.id)}
        ),
        "read": lambda: (
            service.list_messages(user, agent.id, conversation.uuid)[0] == conversation
            and run_type.can_read(user, run)
        ),
        "follow": lambda: run_type.can_follow_chat(user, conversation.id),
        "stop": lambda: run_type.can_cancel(user, run),
        "rename": lambda: (
            service.update_conversation(
                user, agent.id, conversation.uuid, title="Renamed"
            )
            is not None
        ),
        "delete": lambda: (
            service.delete_conversation(user, agent.id, conversation.uuid) is not None
        ),
    }

    with pytest.raises(send_error):
        service.create_message(user, agent.id, conversation.uuid, run.id, "Hello")
    outcomes = {}
    # The order matters: a successful delete ends the conversation's visibility.
    for name in ["list", "read", "follow", "stop", "rename", "delete"]:
        try:
            with transaction.atomic():
                outcomes[name] = bool(attempts[name]())
        except PermissionException:
            outcomes[name] = False

    assert {name for name, ok in outcomes.items() if ok} == allowed
    conversation.refresh_from_db()
    assert conversation.trashed is ("delete" in allowed)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role_uid,changes_own,restores_shared",
    [
        ("VIEWER", False, False),
        ("COMMENTER", False, False),
        ("EDITOR", True, False),
        ("BUILDER", True, True),
    ],
    ids=["viewer", "commenter", "editor", "builder"],
)
def test_editors_change_their_own_conversations_and_builders_restore_shared_ones(
    enterprise_data_fixture,
    enable_enterprise,
    synced_roles,
    role_uid,
    changes_own,
    restores_shared,
):
    """A viewer only reads, even a private conversation left from an older role."""

    admin = enterprise_data_fixture.create_user()
    user = enterprise_data_fixture.create_user()
    workspace = enterprise_data_fixture.create_workspace(user=admin, members=[user])
    RoleAssignmentHandler().assign_role(user, workspace, Role.objects.get(uid=role_uid))
    agent = enterprise_data_fixture.create_agent_application(workspace=workspace)
    shared = enterprise_data_fixture.create_shared_agent_conversation(agent=agent)
    private = enterprise_data_fixture.create_agent_conversation(user=user, agent=agent)
    trashed = enterprise_data_fixture.create_agent_conversation(user=user, agent=agent)
    service = AgentService()
    service.delete_conversation(admin, agent.id, shared.uuid)
    AgentHandler().delete_conversation(user, trashed)

    def own_change() -> contextlib.AbstractContextManager:
        if changes_own:
            return contextlib.nullcontext()
        return pytest.raises(PermissionException)

    with own_change():
        service.update_conversation(user, agent.id, private.uuid, title="Renamed")
    with own_change():
        service.delete_conversation(user, agent.id, private.uuid)
    with own_change():
        TrashHandler.restore_item(user, "agent_conversation", trashed.id)
    with (
        contextlib.nullcontext()
        if restores_shared
        else pytest.raises(PermissionException)
    ):
        TrashHandler.restore_item(user, "agent_conversation", shared.id)

    assert set(AgentConversation.objects.values_list("id", flat=True)) == {
        trashed.id if changes_own else private.id,
        *([shared.id] if restores_shared else []),
    }
