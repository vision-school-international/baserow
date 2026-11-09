import json

import pytest
from rest_framework import serializers

from baserow.contrib.agent.application_types import AgentApplicationType
from baserow.contrib.agent.models import AgentTrigger
from baserow.contrib.agent.triggers.data_providers import (
    AgentTriggerDispatchContext,
    TriggerDataProviderType,
    agent_data_provider_type_registry,
    resolve_trigger_message,
)
from baserow.contrib.agent.validators import AGENT_TEXT_MAX_LENGTH
from baserow.core.formula.serializers import FormulaSerializerField

PAYLOAD = {
    "triggered_at": "2026-11-09T09:00:00+00:00",
    "next_run_at": "2026-11-09T10:00:00+00:00",
}


class MessageSerializer(serializers.Serializer):
    message = FormulaSerializerField()


@pytest.fixture
def periodic_trigger(data_fixture):
    def create(message: str = "") -> AgentTrigger:
        return data_fixture.create_agent_trigger(message=message)

    return create


def test_trigger_provider_is_registered():
    assert isinstance(
        agent_data_provider_type_registry.get("trigger"), TriggerDataProviderType
    )


@pytest.mark.parametrize(
    "formula,valid",
    [("get('trigger.triggered_at')", True), ("get('nowhere.triggered_at')", False)],
)
def test_message_formulas_are_validated_against_the_trigger_provider(formula, valid):
    serializer = MessageSerializer(
        data={"message": formula}, context={"application_type": AgentApplicationType}
    )

    assert serializer.is_valid() is valid, serializer.errors


@pytest.mark.django_db
def test_dispatch_context_exposes_the_payload_as_trigger(periodic_trigger):
    trigger = periodic_trigger()
    context = AgentTriggerDispatchContext(trigger, PAYLOAD)

    assert context["trigger.triggered_at"] == PAYLOAD["triggered_at"]
    assert context["trigger.missing"] is None
    assert context.workspace == trigger.agent.workspace
    assert context.clone().trigger is trigger


@pytest.mark.django_db
def test_get_data_chunk_maps_list_payload_rows_through_the_service_type(
    data_fixture,
):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = data_fixture.create_text_field(user=user, table=table, name="Name")
    agent = data_fixture.create_agent_application(workspace=table.database.workspace)
    service = data_fixture.create_local_baserow_rows_created_service(table=table)
    trigger = data_fixture.create_agent_trigger(agent=agent, service=service)
    payload = {"results": [{"Name": "Horse"}], "has_next_page": False}
    context = AgentTriggerDispatchContext(trigger, payload)
    provider = TriggerDataProviderType()

    assert provider.get_data_chunk(context, ["0", field.db_column]) == "Horse"
    assert provider.get_data_chunk(context, ["0"]) == {"Name": "Horse"}


@pytest.mark.django_db
def test_resolve_trigger_message_resolves_the_formula(periodic_trigger):
    trigger = periodic_trigger("concat('Digest for ', get('trigger.triggered_at'))")

    assert (
        resolve_trigger_message(trigger, PAYLOAD)
        == "Digest for 2026-11-09T09:00:00+00:00"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("message", ["", "' '"])
def test_resolve_trigger_message_falls_back_to_the_payload(periodic_trigger, message):
    trigger = periodic_trigger(message)
    expected = "Trigger data:\n```json\n" + json.dumps(PAYLOAD, indent=2) + "\n```"

    assert resolve_trigger_message(trigger, PAYLOAD) == expected


@pytest.mark.django_db
def test_resolve_trigger_message_cuts_to_the_message_limit(periodic_trigger):
    trigger = periodic_trigger("get('trigger.triggered_at')")
    payload = {"triggered_at": "x" * (AGENT_TEXT_MAX_LENGTH + 1)}

    assert len(resolve_trigger_message(trigger, payload)) == AGENT_TEXT_MAX_LENGTH
