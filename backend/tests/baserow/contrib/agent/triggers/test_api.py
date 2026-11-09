from typing import Any

import pytest

from baserow.contrib.agent.models import AgentApplication, AgentTrigger
from baserow.contrib.integrations.core.service_types import (
    CorePeriodicTriggerServiceType,
)

from ..utils import agent_url

MESSAGE = {"formula": "'Daily digest'", "mode": "simple", "version": "0.1"}


@pytest.fixture
def periodic_trigger(data_fixture):
    def create(agent: AgentApplication, **service_values: Any) -> AgentTrigger:
        service = data_fixture.create_core_periodic_service(**service_values)
        return data_fixture.create_agent_trigger(
            agent=agent, service=service, message=MESSAGE
        )

    return create


@pytest.mark.django_db
def test_configuration_lists_the_available_trigger_types(
    data_fixture, api_client, api_user, mocker
):
    agent = data_fixture.create_agent_application(user=api_user)
    url = agent_url(agent, "configuration")

    assert api_client.get(url).json()["available_trigger_types"] == ["periodic"]

    mocker.patch(
        "baserow.contrib.agent.triggers.handler.AGENT_TRIGGER_TYPES_ENABLED",
        ("periodic", "http_trigger", "manual"),
    )
    assert set(api_client.get(url).json()["available_trigger_types"]) == {
        "periodic",
        "http_trigger",
    }

    mocker.patch.object(
        CorePeriodicTriggerServiceType, "is_deactivated", return_value=True
    )
    assert api_client.get(url).json()["available_trigger_types"] == ["http_trigger"]
