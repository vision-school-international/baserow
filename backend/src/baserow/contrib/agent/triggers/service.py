from django.contrib.auth.models import AbstractUser
from django.db import transaction

from baserow.contrib.agent.handler import AgentHandler
from baserow.contrib.agent.models import AgentApplication, AgentTrigger
from baserow.contrib.agent.operations import ReadAgentConfigurationOperationType
from baserow.core.feature_flags import FF_AGENT_BUILDER, feature_flag_is_enabled
from baserow.core.formula.types import BaserowFormulaObject
from baserow.core.handler import CoreHandler
from baserow.core.operations import UpdateApplicationOperationType
from baserow.core.services.registries import service_type_registry
from baserow.core.types import PermissionCheck

from .exceptions import AgentTriggerTypeNotAvailable
from .handler import AgentTriggerHandler

WRITE_OPERATIONS = (
    UpdateApplicationOperationType.type,
    ReadAgentConfigurationOperationType.type,
)


class AgentTriggerService:
    def __init__(self) -> None:
        self.handler = AgentTriggerHandler()
        self.agent_handler = AgentHandler()

    def _check_permissions(
        self, user: AbstractUser, agent: AgentApplication, *operations: str
    ) -> None:
        """
        Check each operation on the Agent, as the configuration calls do.

        :param user: The user to check.
        :param agent: The Agent the operations apply to.
        :param operations: The operation type names the user needs.
        :raises PermissionException: When the user lacks any of the operations.
        """

        CoreHandler().check_multiple_permissions(
            [PermissionCheck(user, operation, agent) for operation in operations],
            workspace=agent.workspace,
            raise_exception=True,
        )

    def _get_authorized_trigger(
        self,
        user: AbstractUser,
        agent_id: int,
        trigger_id: int,
        *operations: str,
        for_update: bool = False,
    ) -> AgentTrigger:
        """
        Check each operation on a live Agent, then fetch one of its triggers.

        :param user: The user asking for the trigger.
        :param agent_id: The id of the Agent.
        :param trigger_id: The id of the trigger.
        :param operations: The operation type names the user needs on the Agent.
        :param for_update: Whether to lock the Agent and the trigger.
        :raises ApplicationDoesNotExist: When the Agent doesn't exist or is trashed.
        :raises PermissionException: When the user lacks any of the operations.
        :raises AgentTriggerDoesNotExist: When the Agent has no such trigger.
        :return: The trigger with its Agent and service.
        """

        agent = self.agent_handler.get_agent(agent_id, for_update=for_update)
        self._check_permissions(user, agent, *operations)
        queryset = AgentTrigger.objects.filter(agent=agent)
        if for_update:
            queryset = queryset.select_for_update(of=("self",))
        return self.handler.get_trigger(trigger_id, base_queryset=queryset)

    def available_trigger_types(self, agent: AgentApplication) -> list[str]:
        """
        List the trigger types a trigger of this Agent can have.

        :param agent: The Agent the triggers would belong to.
        :return: The service type names the Agent's configuration offers.
        """

        return self.handler.available_trigger_types(agent)

    def list_triggers(self, user: AbstractUser, agent_id: int) -> list[AgentTrigger]:
        """
        Return the Agent's triggers to a user allowed to read its configuration.

        :param user: The user listing the triggers.
        :param agent_id: The id of the Agent.
        :raises ApplicationDoesNotExist: When the Agent doesn't exist or is trashed.
        :raises PermissionException: When the user may not read the configuration.
        :return: The triggers, oldest first.
        """

        agent = self.agent_handler.get_agent(agent_id)
        self._check_permissions(user, agent, ReadAgentConfigurationOperationType.type)
        return list(self.handler.list_triggers(agent))

    def get_trigger(
        self, user: AbstractUser, agent_id: int, trigger_id: int
    ) -> AgentTrigger:
        """
        Return one trigger to a user allowed to read its Agent's configuration.

        :param user: The user reading the trigger.
        :param agent_id: The id of the Agent the trigger belongs to.
        :param trigger_id: The id of the trigger.
        :raises ApplicationDoesNotExist: When the Agent doesn't exist or is trashed.
        :raises AgentTriggerDoesNotExist: When the Agent has no such trigger or it
            is trashed.
        :raises PermissionException: When the user may not read the configuration.
        :return: The trigger with its Agent and service.
        """

        return self._get_authorized_trigger(
            user, agent_id, trigger_id, ReadAgentConfigurationOperationType.type
        )

    @transaction.atomic
    def create_trigger(
        self,
        user: AbstractUser,
        agent_id: int,
        service_type_name: str,
        message: BaserowFormulaObject | str = "",
        enabled: bool = True,
        service_values: dict | None = None,
    ) -> AgentTrigger:
        """
        Add a trigger of an available type to the Agent, for a user who may update
        and read its configuration.

        :param user: The user adding the trigger.
        :param agent_id: The id of the Agent.
        :param service_type_name: The service type of the trigger.
        :param message: The formula whose text opens each conversation it starts.
        :param enabled: Whether the trigger starts conversations right away.
        :param service_values: Initial values of the service, by field name, or
            None to leave it unconfigured.
        :raises FeatureDisabledException: When Agents are disabled.
        :raises ApplicationDoesNotExist: When the Agent doesn't exist or is trashed.
        :raises PermissionException: When the user may not update the Agent or read
            its configuration.
        :raises AgentTriggerTypeNotAvailable: When the type isn't one the Agent's
            configuration offers.
        :raises TriggerServiceMisconfigured: When the service values are invalid.
        :return: The created trigger, armed when its service is configured.
        """

        feature_flag_is_enabled(FF_AGENT_BUILDER, raise_if_disabled=True)
        agent = self.agent_handler.get_agent(agent_id, for_update=True)
        self._check_permissions(user, agent, *WRITE_OPERATIONS)
        if service_type_name not in self.available_trigger_types(agent):
            raise AgentTriggerTypeNotAvailable(service_type_name)
        service_type = service_type_registry.get(service_type_name)
        prepared_service_values = service_type.prepare_values(
            service_values or {}, user
        )
        return self.handler.create_trigger(
            agent,
            service_type,
            prepared_service_values,
            message=message,
            enabled=enabled,
        )

    @transaction.atomic
    def update_trigger(
        self,
        user: AbstractUser,
        agent_id: int,
        trigger_id: int,
        enabled: bool | None = None,
        message: BaserowFormulaObject | str | None = None,
        service_values: dict | None = None,
    ) -> AgentTrigger:
        """
        Change a trigger's switch, message or service values, for a user who may
        update and read its Agent's configuration.

        :param user: The user updating the trigger.
        :param agent_id: The id of the Agent the trigger belongs to.
        :param trigger_id: The id of the trigger.
        :param enabled: The new switch state, or None to keep it.
        :param message: The new message formula, or None to keep it.
        :param service_values: The service values to set, by field name, or None.
        :raises FeatureDisabledException: When Agents are disabled.
        :raises ApplicationDoesNotExist: When the Agent doesn't exist or is trashed.
        :raises AgentTriggerDoesNotExist: When the Agent has no such trigger or it
            is trashed.
        :raises PermissionException: When the user may not update the Agent or read
            its configuration.
        :raises TriggerServiceMisconfigured: When the service values are invalid.
        :return: The updated trigger.
        """

        feature_flag_is_enabled(FF_AGENT_BUILDER, raise_if_disabled=True)
        # Locked so two debounced saves of one card can't lose each other's fields.
        trigger = self._get_authorized_trigger(
            user, agent_id, trigger_id, *WRITE_OPERATIONS, for_update=True
        )
        prepared_service_values = None
        if service_values is not None:
            service = trigger.service.specific
            prepared_service_values = service.get_type().prepare_values(
                service_values, user, service
            )
        return self.handler.update_trigger(
            trigger,
            enabled=enabled,
            message=message,
            prepared_service_values=prepared_service_values,
        )

    @transaction.atomic
    def delete_trigger(
        self, user: AbstractUser, agent_id: int, trigger_id: int
    ) -> AgentTrigger:
        """
        Move a trigger to the trash, for a user who may update and read its Agent's
        configuration.

        :param user: The user deleting the trigger.
        :param agent_id: The id of the Agent the trigger belongs to.
        :param trigger_id: The id of the trigger.
        :raises FeatureDisabledException: When Agents are disabled.
        :raises ApplicationDoesNotExist: When the Agent doesn't exist or is trashed.
        :raises AgentTriggerDoesNotExist: When the Agent has no such trigger or it
            is trashed already.
        :raises PermissionException: When the user may not update the Agent or read
            its configuration.
        :return: The trashed trigger.
        """

        feature_flag_is_enabled(FF_AGENT_BUILDER, raise_if_disabled=True)
        trigger = self._get_authorized_trigger(
            user, agent_id, trigger_id, *WRITE_OPERATIONS, for_update=True
        )
        self.handler.delete_trigger(user, trigger)
        return trigger
