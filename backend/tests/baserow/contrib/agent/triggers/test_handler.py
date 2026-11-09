from datetime import datetime, timezone

import pytest
from freezegun import freeze_time

from baserow.contrib.agent.models import AgentTrigger
from baserow.contrib.agent.triggers.exceptions import AgentTriggerDoesNotExist
from baserow.contrib.agent.triggers.handler import AgentTriggerHandler
from baserow.contrib.integrations.core.constants import (
    PERIODIC_INTERVAL_DAY,
    PERIODIC_INTERVAL_HOUR,
)
from baserow.contrib.integrations.core.models import CorePeriodicService
from baserow.contrib.integrations.core.service_types import (
    CorePeriodicTriggerServiceType,
)
from baserow.core.services.registries import service_type_registry


def daily_trigger(data_fixture, **kwargs) -> AgentTrigger:
    service = data_fixture.create_core_periodic_service(
        interval=PERIODIC_INTERVAL_DAY, hour=9
    )
    return data_fixture.create_agent_trigger(service=service, **kwargs)


@pytest.mark.django_db
def test_create_trigger_creates_an_armed_service(data_fixture):
    agent = data_fixture.create_agent_application()

    with freeze_time("2026-01-01 08:00"):
        trigger = AgentTriggerHandler().create_trigger(
            agent,
            service_type_registry.get("periodic"),
            {"interval": PERIODIC_INTERVAL_DAY, "hour": 9, "minute": 0},
            message="'Daily digest'",
        )

    service = CorePeriodicService.objects.get(id=trigger.service_id)
    assert (trigger.agent, trigger.enabled) == (agent, True)
    assert trigger.message["formula"] == "'Daily digest'"
    assert (service.interval, service.hour) == (PERIODIC_INTERVAL_DAY, 9)
    assert service.next_run_at == datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    assert AgentTriggerHandler().list_triggers(agent).get() == trigger


@pytest.mark.django_db
def test_update_trigger_rearms_only_for_a_new_schedule_or_switching_on(
    data_fixture, mocker
):
    trigger = daily_trigger(data_fixture, enabled=False)
    arm = mocker.patch.object(CorePeriodicTriggerServiceType, "arm")
    handler = AgentTriggerHandler()

    handler.update_trigger(trigger, message="'Changed'")
    handler.update_trigger(
        trigger, prepared_service_values={"interval": PERIODIC_INTERVAL_DAY, "hour": 9}
    )
    handler.update_trigger(trigger, enabled=False)
    assert arm.call_count == 0

    handler.update_trigger(
        trigger,
        prepared_service_values={"interval": PERIODIC_INTERVAL_HOUR, "minute": 30},
    )
    handler.update_trigger(trigger, enabled=True)
    assert arm.call_count == 2

    trigger.refresh_from_db()
    service = CorePeriodicService.objects.get(id=trigger.service_id)
    assert (trigger.enabled, trigger.message["formula"]) == (True, "'Changed'")
    assert (service.interval, service.minute) == (PERIODIC_INTERVAL_HOUR, 30)


@pytest.mark.django_db
def test_get_trigger_loads_the_agent_workspace_and_service_in_one_query(
    data_fixture, django_assert_num_queries
):
    trigger = daily_trigger(data_fixture)
    expected = (trigger.agent.workspace_id, trigger.service_id)

    with django_assert_num_queries(1):
        found = AgentTriggerHandler().get_trigger(trigger.id)
        assert (found.agent.workspace.id, found.service.id) == expected

    with pytest.raises(AgentTriggerDoesNotExist):
        AgentTriggerHandler().get_trigger(trigger.id + 1)
