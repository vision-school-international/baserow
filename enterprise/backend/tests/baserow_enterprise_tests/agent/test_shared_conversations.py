from django.db import transaction

import pytest

from baserow.contrib.agent.chat_run_type import AgentChatRunType
from baserow.contrib.agent.exceptions import AgentConversationReadOnly
from baserow.contrib.agent.handler import AgentHandler
from baserow.contrib.agent.service import AgentService
from baserow.core.chat_runs.models import ChatRun
from baserow.core.exceptions import PermissionException
from baserow_enterprise.role.handler import RoleAssignmentHandler
from baserow_enterprise.role.models import Role

READ = {"list", "read", "follow"}
CHANGE = READ | {"stop", "rename", "delete"}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role_uid,allowed,send_error",
    [
        (None, set(), PermissionException),
        ("VIEWER", READ, PermissionException),
        ("EDITOR", READ, AgentConversationReadOnly),
        ("BUILDER", CHANGE, AgentConversationReadOnly),
        ("ADMIN", CHANGE, AgentConversationReadOnly),
    ],
    ids=["non-member", "viewer", "editor", "builder", "admin"],
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
        ),
        "follow": lambda: (
            run_type.can_follow_chat(user, conversation.id)
            and run_type.can_read(user, run)
        ),
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
