from typing import Any

from django.contrib.auth.models import AbstractUser

import pytest

from baserow.contrib.agent.models import AgentApplication, AgentTrigger
from baserow.contrib.agent.operations import ReadAgentConfigurationOperationType
from baserow.contrib.agent.triggers.actions import (
    CreateAgentTriggerActionType,
    DeleteAgentTriggerActionType,
    UpdateAgentTriggerActionType,
)
from baserow.contrib.agent.triggers.exceptions import AgentTriggerTypeNotAvailable
from baserow.contrib.agent.triggers.service import AgentTriggerService
from baserow.contrib.integrations.core.service_types import (
    CorePeriodicTriggerServiceType,
)
from baserow.core.action.registries import action_type_registry
from baserow.core.exceptions import FeatureDisabledException
from baserow.core.handler import CoreHandler
from baserow.core.operations import UpdateApplicationOperationType

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


def call(
    name: str, user: AbstractUser, agent: AgentApplication, trigger: AgentTrigger
) -> Any:
    service = AgentTriggerService()
    calls = {
        "list": lambda: service.list_triggers(user, agent.id),
        "get": lambda: service.get_trigger(user, trigger.id),
        "create": lambda: service.create_trigger(user, agent.id, "periodic"),
        "update": lambda: service.update_trigger(user, trigger.id, enabled=False),
        "delete": lambda: service.delete_trigger(user, trigger.id),
    }
    return calls[name]()


def test_trigger_action_types_are_registered():
    for action_type in (
        CreateAgentTriggerActionType,
        UpdateAgentTriggerActionType,
        DeleteAgentTriggerActionType,
    ):
        assert isinstance(action_type_registry.get(action_type.type), action_type)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name,operations",
    [
        ("list", [ReadAgentConfigurationOperationType]),
        ("get", [ReadAgentConfigurationOperationType]),
        (
            "create",
            [UpdateApplicationOperationType, ReadAgentConfigurationOperationType],
        ),
        (
            "update",
            [UpdateApplicationOperationType, ReadAgentConfigurationOperationType],
        ),
        (
            "delete",
            [UpdateApplicationOperationType, ReadAgentConfigurationOperationType],
        ),
    ],
)
def test_each_trigger_call_checks_its_operations_on_the_agent(
    data_fixture, periodic_trigger, mocker, name, operations
):
    user = data_fixture.create_user()
    agent = data_fixture.create_agent_application(user=user)
    trigger = periodic_trigger(agent)
    check = mocker.spy(CoreHandler, "check_multiple_permissions")

    call(name, user, agent, trigger)

    assert [
        (permission.operation_name, permission.context.id)
        for args, _ in check.call_args_list
        for permission in args[1]
    ] == [(operation.type, agent.id) for operation in operations]


@pytest.mark.django_db
@pytest.mark.parametrize("write", ["create", "update", "delete"])
def test_trigger_writes_need_the_feature_flag(
    data_fixture, periodic_trigger, settings, write
):
    user = data_fixture.create_user()
    agent = data_fixture.create_agent_application(user=user)
    trigger = periodic_trigger(agent)
    settings.FEATURE_FLAGS = []

    with pytest.raises(FeatureDisabledException):
        call(write, user, agent, trigger)

    trigger.refresh_from_db()
    assert (AgentTrigger.objects.count(), trigger.enabled, trigger.trashed) == (
        1,
        True,
        False,
    )


@pytest.mark.django_db
def test_create_trigger_action_rejects_a_type_the_agent_can_not_use(data_fixture):
    user = data_fixture.create_user()
    agent = data_fixture.create_agent_application(user=user)
    action = action_type_registry.get_by_type(CreateAgentTriggerActionType)

    for type_name in ("manual", "http_trigger", "upsert_row", "unknown"):
        with pytest.raises(AgentTriggerTypeNotAvailable):
            action.do(user, agent.id, type_name)

    assert not AgentTrigger.objects.exists()
