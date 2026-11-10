from dataclasses import dataclass

from django.contrib.auth.models import AbstractUser
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from baserow.contrib.agent.models import AgentTrigger
from baserow.core.action.registries import (
    ActionScopeStr,
    ActionType,
    ActionTypeDescription,
)
from baserow.core.action.scopes import ApplicationActionScopeType
from baserow.core.formula.types import BaserowFormulaObject

from .service import AgentTriggerService


class CreateAgentTriggerActionType(ActionType):
    type = "create_agent_trigger"
    description = ActionTypeDescription(
        _("Create agent trigger"),
        _(
            "Trigger (%(trigger_id)s) of type %(trigger_type)s created in agent "
            "(%(agent_id)s)."
        ),
    )
    analytics_params = ["agent_id", "trigger_type"]

    @dataclass
    class Params:
        agent_id: int
        trigger_id: int
        trigger_type: str

    @classmethod
    @transaction.atomic
    def do(
        cls,
        user: AbstractUser,
        agent_id: int,
        service_type_name: str,
        message: BaserowFormulaObject | str = "",
        enabled: bool = True,
        **service_values: object,
    ) -> AgentTrigger:
        """
        Add a trigger to an Agent and audit its type.

        :param user: The user adding the trigger.
        :param agent_id: The id of the Agent.
        :param service_type_name: The service type of the trigger.
        :param message: The formula whose text opens each conversation it starts.
        :param enabled: Whether the trigger starts conversations right away.
        :param service_values: Initial values of the service, by field name.
        :return: The created trigger.
        """

        trigger = AgentTriggerService().create_trigger(
            user,
            agent_id,
            service_type_name,
            message=message,
            enabled=enabled,
            **service_values,
        )
        cls.register_action(
            user,
            cls.Params(agent_id, trigger.id, service_type_name),
            cls.scope(agent_id),
            trigger.agent.workspace,
        )
        return trigger

    @classmethod
    def scope(cls, agent_id: int) -> ActionScopeStr:
        """
        Scope the action to the Agent whose triggers it changes.

        :param agent_id: The id of the Agent.
        :return: The application scope of the Agent.
        """

        return ApplicationActionScopeType.value(agent_id)


class UpdateAgentTriggerActionType(ActionType):
    type = "update_agent_trigger"
    description = ActionTypeDescription(
        _("Update agent trigger"),
        _("Trigger (%(trigger_id)s) updated in agent (%(agent_id)s)."),
    )
    analytics_params = ["agent_id", "trigger_type", "changed_fields"]

    @dataclass
    class Params:
        agent_id: int
        trigger_id: int
        trigger_type: str
        changed_fields: list[str]

    @classmethod
    @transaction.atomic
    def do(
        cls,
        user: AbstractUser,
        agent_id: int,
        trigger_id: int,
        enabled: bool | None = None,
        message: BaserowFormulaObject | str | None = None,
        service: dict | None = None,
    ) -> AgentTrigger:
        """
        Change a trigger and audit which of its parts were given, never their
        values: the message and service values are configuration.

        :param user: The user updating the trigger.
        :param agent_id: The id of the Agent the trigger belongs to.
        :param trigger_id: The id of the trigger.
        :param enabled: The new switch state, or None to keep it.
        :param message: The new message formula, or None to keep it.
        :param service: The service values to set, by field name, or None.
        :return: The updated trigger.
        """

        trigger = AgentTriggerService().update_trigger(
            user,
            agent_id,
            trigger_id,
            enabled=enabled,
            message=message,
            service_values=service,
        )
        given = (("enabled", enabled), ("message", message), ("service", service))
        cls.register_action(
            user,
            cls.Params(
                trigger.agent_id,
                trigger.id,
                trigger.service.get_type().type,
                [name for name, value in given if value is not None],
            ),
            cls.scope(trigger.agent_id),
            trigger.agent.workspace,
        )
        return trigger

    @classmethod
    def scope(cls, agent_id: int) -> ActionScopeStr:
        """
        Scope the action to the Agent whose triggers it changes.

        :param agent_id: The id of the Agent.
        :return: The application scope of the Agent.
        """

        return ApplicationActionScopeType.value(agent_id)


class DeleteAgentTriggerActionType(ActionType):
    type = "delete_agent_trigger"
    description = ActionTypeDescription(
        _("Delete agent trigger"),
        _("Trigger (%(trigger_id)s) deleted in agent (%(agent_id)s)."),
    )
    analytics_params = ["agent_id", "trigger_type"]

    @dataclass
    class Params:
        agent_id: int
        trigger_id: int
        trigger_type: str

    @classmethod
    @transaction.atomic
    def do(cls, user: AbstractUser, agent_id: int, trigger_id: int) -> None:
        """
        Move a trigger to the trash and audit its type.

        :param user: The user deleting the trigger.
        :param agent_id: The id of the Agent the trigger belongs to.
        :param trigger_id: The id of the trigger.
        """

        trigger = AgentTriggerService().delete_trigger(user, agent_id, trigger_id)
        cls.register_action(
            user,
            cls.Params(trigger.agent_id, trigger.id, trigger.service.get_type().type),
            cls.scope(trigger.agent_id),
            trigger.agent.workspace,
        )

    @classmethod
    def scope(cls, agent_id: int) -> ActionScopeStr:
        """
        Scope the action to the Agent whose triggers it changes.

        :param agent_id: The id of the Agent.
        :return: The application scope of the Agent.
        """

        return ApplicationActionScopeType.value(agent_id)
