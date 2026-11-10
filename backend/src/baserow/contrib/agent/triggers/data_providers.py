import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from baserow.contrib.agent.models import AgentTrigger
from baserow.contrib.agent.validators import AGENT_TEXT_MAX_LENGTH
from baserow.core.formula import resolve_formula
from baserow.core.formula.registries import (
    DataProviderType,
    DataProviderTypeRegistry,
    formula_runtime_function_registry,
)
from baserow.core.formula.types import BaserowFormulaObject
from baserow.core.formula.validator import ensure_string
from baserow.core.services.dispatch_context import DispatchContext
from baserow.core.services.models import Service
from baserow.core.utils import get_value_at_path

agent_data_provider_type_registry = DataProviderTypeRegistry()

FIRED_AT_PATH = "fired_at"
FIRED_AT_FORMAT = "%Y-%m-%d %H:%M"
FIRED_AT_DEFAULT_TIMEZONE = "UTC"


class AgentTriggerDispatchContext(DispatchContext):
    """
    The context a trigger message formula is resolved in: the trigger that fired,
    the payload its service produced for the event and the moment it fired.
    """

    own_properties = ["trigger", "event_payload", "fired_at"]

    def __init__(
        self, trigger: AgentTrigger, event_payload: dict[str, Any], fired_at: datetime
    ) -> None:
        """
        :param trigger: The trigger whose message is being resolved.
        :param event_payload: The payload the trigger's service produced for this
            event, in the shape its `generate_schema` describes.
        :param fired_at: When the dispatcher handled the event.
        """

        self.trigger = trigger
        self.fired_at = fired_at
        super().__init__(event_payload=event_payload, workspace=trigger.agent.workspace)

    @property
    def data_provider_registry(self) -> DataProviderTypeRegistry:
        """
        :return: The registry `get('<provider>.…')` looks providers up in.
        """

        return agent_data_provider_type_registry

    @property
    def service(self) -> Service:
        """
        :return: The trigger's service in its specific form.
        """

        return self.trigger.service.specific

    def get_fired_at_display(self) -> str:
        """
        :return: When the trigger fired, as `YYYY-MM-DD HH:mm (Zone/Name)` in the
            timezone its service runs in, or in UTC when the type has none.
        """

        service = self.service
        zone_name = (
            service.get_type().get_timezone_name(service) or FIRED_AT_DEFAULT_TIMEZONE
        )
        local = self.fired_at.astimezone(ZoneInfo(zone_name))
        return f"{local.strftime(FIRED_AT_FORMAT)} ({zone_name})"


class TriggerDataProviderType(DataProviderType):
    """
    Exposes the payload of the trigger that started the conversation as the
    `trigger` provider, so a trigger message can read `get('trigger.<property>')`.
    Every trigger also offers `trigger.fired_at`, computed here and never part of
    the service payload; it takes precedence over a payload key of that name.
    """

    type = "trigger"

    def get_data_chunk(
        self, dispatch_context: AgentTriggerDispatchContext, path: list[str]
    ) -> Any:
        """
        Read a value of the event payload. A list service keeps its rows under
        `results`, so the first path part is the row index and the service type
        maps the rest (for example a `field_<id>` db column to the field name).

        :param dispatch_context: The context holding the trigger and its payload.
        :param path: The path parts after the provider name.
        :return: The value at the path, or `None` when there is none.
        """

        if path == [FIRED_AT_PATH]:
            return dispatch_context.get_fired_at_display()

        service = dispatch_context.service
        service_type = service.get_type()
        payload = dispatch_context.event_payload

        if service_type.returns_list:
            payload = payload["results"]
            if len(path) >= 2:
                prepared_path = [
                    path[0],
                    *service_type.prepare_value_path(service, path[1:]),
                ]
            else:
                prepared_path = path
        else:
            prepared_path = service_type.prepare_value_path(service, path)

        return get_value_at_path(payload, prepared_path)

    def import_path(
        self, path: list[str], id_mapping: dict[str, Any], **kwargs: Any
    ) -> list[str]:
        """
        Trigger paths name payload properties, not ids, so they import unchanged.

        :param path: The path parts after the provider name.
        :param id_mapping: The id mapping of the import.
        :return: The same path.
        """

        return path


def _payload_as_message(event_payload: dict[str, Any]) -> str:
    """
    :param event_payload: The payload the trigger's service produced.
    :return: The payload as a fenced JSON block, the opening message when the
        trigger has no message of its own.
    """

    payload = json.dumps(event_payload, default=str, indent=2)
    return f"Trigger data:\n```json\n{payload}\n```"


def resolve_trigger_message(
    trigger: AgentTrigger, event_payload: dict[str, Any], fired_at: datetime
) -> str:
    """
    Resolve the trigger's message formula against the event payload. An empty
    result opens the conversation with the payload itself as fenced JSON, so a
    trigger with no message still tells the agent what happened.

    :param trigger: The trigger that fired.
    :param event_payload: The payload its service produced for this event.
    :param fired_at: When the dispatcher handled the event.
    :return: The content of the message that opens the conversation, cut to the
        length the API accepts for a message.
    """

    content = ensure_string(
        resolve_formula(
            BaserowFormulaObject.to_formula(trigger.message),
            formula_runtime_function_registry,
            AgentTriggerDispatchContext(trigger, event_payload, fired_at),
        )
    )
    if not content.strip():
        content = _payload_as_message(event_payload)
    return content[:AGENT_TEXT_MAX_LENGTH]
