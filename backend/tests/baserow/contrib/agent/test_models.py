import pytest

from baserow.contrib.agent.models import AgentMessage, AgentTrigger


@pytest.mark.django_db
def test_agent_trigger_defaults_and_trash_managers(data_fixture):
    agent = data_fixture.create_agent_application()
    trigger = data_fixture.create_agent_trigger(agent=agent)
    trashed = data_fixture.create_agent_trigger(agent=agent, trashed=True)

    assert trigger.enabled is True
    assert trigger.message["formula"] == ""
    assert trigger.service.agent_trigger == trigger
    assert list(AgentTrigger.objects.filter(agent=agent)) == [trigger]
    assert list(AgentTrigger.objects_and_trash.filter(agent=agent).order_by("id")) == [
        trigger,
        trashed,
    ]


@pytest.mark.django_db
def test_shared_conversation_has_no_owner_and_outlives_its_trigger(data_fixture):
    trigger = data_fixture.create_agent_trigger()
    conversation = data_fixture.create_agent_conversation(
        agent=trigger.agent, owner_user=None, trigger=trigger
    )

    trigger.delete()
    conversation.refresh_from_db()

    assert conversation.owner_user is None
    assert conversation.trigger is None


@pytest.mark.django_db
def test_trigger_role_replaces_the_unused_system_role(data_fixture):
    message = data_fixture.create_agent_message(role=AgentMessage.Role.TRIGGER)

    assert message.role == "trigger"
    assert set(AgentMessage.Role.values) == {"user", "assistant", "trigger"}
