from datetime import datetime, timezone
from uuid import uuid4

from django.test import override_settings

import pytest

from baserow.contrib.agent.actions import CreateAgentConversationActionType
from baserow.contrib.agent.handler import AgentHandler
from baserow.contrib.agent.models import (
    AgentApplication,
    AgentConversation,
    AgentMessage,
    AgentTrigger,
)
from baserow.contrib.integrations.core.constants import PERIODIC_INTERVAL_MINUTE
from baserow.core.action.registries import action_type_registry
from baserow.core.chat_runs.models import ChatRun

DUE_AT = datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)


def periodic_trigger(data_fixture, agent: AgentApplication, **kwargs) -> AgentTrigger:
    """A minute trigger due at ``DUE_AT``, with a fixed-text message formula."""

    service = data_fixture.create_core_periodic_service(
        interval=PERIODIC_INTERVAL_MINUTE, minute=1, next_run_at=DUE_AT
    )
    kwargs.setdefault("message", "'Check the inbox'")
    return data_fixture.create_agent_trigger(agent=agent, service=service, **kwargs)


@pytest.mark.django_db
def test_a_trigger_conversation_is_shared_and_answered_by_a_system_run(
    data_fixture, configured_agent
):
    user = data_fixture.create_user()
    agent = configured_agent(user=user)
    trigger = periodic_trigger(data_fixture, agent)

    conversation = AgentHandler().start_trigger_conversation(
        trigger, "  Check\nthe inbox  "
    )

    message, reply = AgentMessage.objects.order_by("id")
    run = ChatRun.objects.get()
    assert conversation == AgentConversation.objects.get()
    assert (conversation.owner_user_id, conversation.trigger_id) == (None, trigger.id)
    assert conversation.title == "Check the inbox"
    assert (message.role, message.content) == ("trigger", "  Check\nthe inbox  ")
    assert (reply.role, reply.status, reply.content) == ("assistant", "running", "")
    assert (run.chat_id, run.created_by, run.status, run.context) == (
        conversation.id,
        None,
        "queued",
        {"reply_id": reply.id},
    )


@pytest.mark.django_db
@override_settings(BASEROW_AGENT_MAX_ACTIVE_RUNS_PER_WORKSPACE=1)
def test_a_trigger_conversation_records_the_run_limit_on_its_reply(
    data_fixture, configured_agent
):
    user = data_fixture.create_user()
    agent = configured_agent(user=user)
    action_type_registry.get_by_type(CreateAgentConversationActionType).do(
        user, agent.id, uuid4(), uuid4(), "Hi"
    )
    trigger = periodic_trigger(data_fixture, agent)

    conversation = AgentHandler().start_trigger_conversation(trigger, "Check the inbox")

    reply = AgentMessage.objects.get(conversation=conversation, role="assistant")
    assert (reply.status, reply.error_code) == ("failed", "chat_run_limit_reached")
    assert AgentConversation.objects.count() == 2
    assert ChatRun.objects.count() == 1
