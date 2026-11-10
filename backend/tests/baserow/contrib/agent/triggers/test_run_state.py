from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event

from django.db import connections, transaction
from django.test import override_settings

import pytest
from freezegun import freeze_time

from baserow.contrib.agent.constants import AGENT_RUN_TYPE
from baserow.contrib.agent.handler import AgentHandler
from baserow.contrib.agent.models import (
    AgentConversation,
    AgentMessage,
    AgentTrigger,
)
from baserow.contrib.agent.triggers.handler import AgentTriggerHandler
from baserow.core.chat_runs.handler import ChatRunHandler
from baserow.core.chat_runs.models import ChatRun
from baserow.core.trash.handler import TrashHandler


def trigger_reply(
    data_fixture, trigger: AgentTrigger, status: str, **conversation_kwargs
) -> AgentMessage:
    """A reply with the given status, in a new conversation of the trigger."""

    conversation = data_fixture.create_shared_agent_conversation(
        agent=trigger.agent, trigger=trigger, **conversation_kwargs
    )
    return data_fixture.create_agent_message(
        conversation=conversation,
        role=AgentMessage.Role.ASSISTANT,
        content="",
        status=status,
    )


def queued_reply(
    trigger: AgentTrigger, content: str = "Check the inbox"
) -> AgentMessage:
    """A trigger conversation started without a run, as a waiting firing queues it."""

    return (
        AgentHandler()
        .start_trigger_conversation(trigger, content, start_run=False)
        .reply
    )


@pytest.mark.django_db
@pytest.mark.parametrize("going_status", ["running", "waiting"])
def test_queued_and_going_replies_are_told_apart(data_fixture, going_status):
    trigger = data_fixture.create_agent_trigger()
    other = data_fixture.create_agent_trigger(agent=trigger.agent)
    for status in ("completed", "failed", "cancelled"):
        trigger_reply(data_fixture, trigger, status)
    trigger_reply(data_fixture, other, going_status)
    first = trigger_reply(data_fixture, trigger, "queued")
    second = trigger_reply(data_fixture, trigger, "queued")
    trigger_reply(data_fixture, trigger, "queued", trashed=True)
    handler = AgentTriggerHandler()

    assert handler.has_going_reply(trigger) is False
    assert handler.count_queued_replies(trigger) == 2
    assert list(handler.get_queued_replies(trigger)) == [first, second]

    trigger_reply(data_fixture, trigger, going_status)

    assert handler.has_going_reply(trigger) is True


@pytest.mark.django_db
def test_the_sweep_lists_only_idle_triggers_with_queued_replies(
    data_fixture, django_assert_num_queries
):
    idle = data_fixture.create_agent_trigger()
    busy, finished, trashed = (
        data_fixture.create_agent_trigger(agent=idle.agent, trashed=is_trashed)
        for is_trashed in (False, False, True)
    )
    for trigger in (idle, busy, trashed):
        trigger_reply(data_fixture, trigger, "queued")
    trigger_reply(data_fixture, busy, "running")
    trigger_reply(data_fixture, finished, "completed")

    with django_assert_num_queries(1):
        idle_triggers = list(
            AgentTriggerHandler().list_idle_triggers_with_queued_replies()
        )

    assert idle_triggers == [idle]


@pytest.mark.django_db
def test_recent_conversation_times_count_what_triggers_started(data_fixture):
    trigger = data_fixture.create_agent_trigger()
    agent = trigger.agent
    sibling = data_fixture.create_agent_trigger(agent=agent)
    stranger = data_fixture.create_agent_trigger()
    created = {}
    for name, owner, at, extra in [
        ("old", trigger, "2026-11-10 09:00", {}),
        ("own", trigger, "2026-11-10 09:40", {}),
        ("deleted", trigger, "2026-11-10 09:45", {"trashed": True}),
        ("sibling", sibling, "2026-11-10 09:50", {}),
        ("stranger", stranger, "2026-11-10 09:55", {}),
    ]:
        with freeze_time(at):
            created[name] = data_fixture.create_shared_agent_conversation(
                agent=owner.agent, trigger=owner, **extra
            ).created_on
    with freeze_time("2026-11-10 09:58"):
        data_fixture.create_agent_conversation(agent=agent)
    since = datetime(2026, 11, 10, 9, 30, tzinfo=timezone.utc)
    handler = AgentTriggerHandler()

    assert sorted(handler.recent_conversation_times(trigger, since)) == [
        created["own"],
        created["deleted"],
    ]
    assert sorted(handler.recent_agent_conversation_times(agent, since)) == [
        created["own"],
        created["deleted"],
        created["sibling"],
    ]


@pytest.mark.django_db
def test_a_skip_and_a_firing_are_recorded_without_touching_updated_on(
    data_fixture,
):
    trigger = data_fixture.create_agent_trigger()
    updated_on = trigger.updated_on
    skipped_at = datetime(2026, 11, 10, 10, 42, tzinfo=timezone.utc)
    fired_at = skipped_at + timedelta(minutes=1)
    handler = AgentTriggerHandler()

    handler.record_skip(trigger, AgentTrigger.SkipReason.QUEUE_FULL, skipped_at)
    handler.record_fired(trigger, fired_at)

    trigger.refresh_from_db()
    assert (
        trigger.last_skipped_on,
        trigger.last_skipped_reason,
        trigger.last_fired_on,
        trigger.updated_on,
    ) == (skipped_at, "queue_full", fired_at, updated_on)


@pytest.mark.django_db
def test_a_trigger_conversation_can_be_queued_without_a_run(
    data_fixture, configured_agent
):
    agent = configured_agent(user=data_fixture.create_user())
    trigger = data_fixture.create_agent_trigger(agent=agent)

    reply = queued_reply(trigger)

    message = reply.conversation.messages.get(role=AgentMessage.Role.TRIGGER)
    assert (message.content, reply.status, reply.content) == (
        "Check the inbox",
        "queued",
        "",
    )
    assert not ChatRun.objects.exists()


@pytest.mark.django_db
def test_the_oldest_queued_reply_starts_once_nothing_is_going(
    data_fixture, configured_agent
):
    agent = configured_agent(user=data_fixture.create_user())
    trigger = data_fixture.create_agent_trigger(agent=agent)
    handler = AgentHandler()
    going = handler.start_trigger_conversation(trigger, "Still going").conversation
    first, second = queued_reply(trigger, "First"), queued_reply(trigger, "Second")

    assert handler.start_next_queued_reply(trigger) is None

    going.messages.filter(role=AgentMessage.Role.ASSISTANT).update(status="completed")
    started = handler.start_next_queued_reply(trigger)

    run = ChatRun.objects.get(chat_id=first.conversation_id)
    second.refresh_from_db()
    assert started == first
    assert (started.status, second.status) == ("running", "queued")
    assert (run.created_by, run.context) == (None, {"reply_id": first.id})
    assert handler.start_next_queued_reply(trigger) is None


@pytest.mark.django_db
@override_settings(BASEROW_AGENT_MAX_ACTIVE_RUNS_PER_WORKSPACE=1)
def test_a_queued_reply_fails_on_the_run_limit_like_a_direct_start(
    data_fixture, configured_agent
):
    user = data_fixture.create_user()
    agent = configured_agent(user=user)
    trigger = data_fixture.create_agent_trigger(agent=agent)
    private = data_fixture.create_agent_conversation(user=user, agent=agent)
    ChatRun.objects.create(
        run_type=AGENT_RUN_TYPE,
        chat_id=private.id,
        workspace=agent.workspace,
        created_by=user,
    )
    reply = queued_reply(trigger)

    assert AgentHandler().start_queued_reply(reply) is None

    reply.refresh_from_db()
    assert (reply.status, reply.error_code) == ("failed", "chat_run_limit_reached")
    assert ChatRun.objects.count() == 1


@pytest.mark.django_db
def test_permanently_deleting_a_trigger_cancels_its_queued_replies(data_fixture):
    user = data_fixture.create_user()
    agent = data_fixture.create_agent_application(user=user)
    trigger = data_fixture.create_agent_trigger(agent=agent)
    queued = trigger_reply(data_fixture, trigger, "queued")
    AgentTriggerHandler().delete_trigger(user, trigger)

    queued.refresh_from_db()
    assert queued.status == "queued"

    TrashHandler.permanently_delete(trigger)

    queued.refresh_from_db()
    conversation = AgentConversation.objects.get(id=queued.conversation_id)
    assert (queued.status, conversation.trigger_id) == ("cancelled", None)


@pytest.mark.django_db(transaction=True)
def test_a_trigger_locked_by_another_caller_starts_nothing_without_waiting(
    data_fixture, configured_agent, mocker
):
    mocker.patch.object(ChatRunHandler, "_enqueue")
    agent = configured_agent(user=data_fixture.create_user())
    trigger = data_fixture.create_agent_trigger(agent=agent)
    reply = queued_reply(trigger)
    locked, release = Event(), Event()

    def hold_the_trigger_lock():
        try:
            with transaction.atomic():
                AgentTrigger.objects.select_for_update().get(id=trigger.id)
                locked.set()
                assert release.wait(10), "The lock was never released"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as executor:
        holder = executor.submit(hold_the_trigger_lock)
        try:
            assert locked.wait(10)
            assert AgentHandler().start_next_queued_reply(trigger) is None
        finally:
            release.set()
        holder.result(timeout=10)

    assert AgentHandler().start_next_queued_reply(trigger) == reply
    assert ChatRun.objects.get().context == {"reply_id": reply.id}
