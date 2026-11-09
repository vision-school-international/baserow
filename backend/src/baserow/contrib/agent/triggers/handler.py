from django.contrib.auth.models import AbstractUser
from django.db.models import QuerySet

from baserow.contrib.agent.models import AgentApplication, AgentTrigger
from baserow.core.formula.types import BaserowFormulaObject
from baserow.core.services.handler import ServiceHandler
from baserow.core.services.registries import TriggerServiceTypeMixin
from baserow.core.trash.handler import TrashHandler

from .exceptions import AgentTriggerDoesNotExist


class AgentTriggerHandler:
    def get_trigger(
        self, trigger_id: int, base_queryset: QuerySet[AgentTrigger] | None = None
    ) -> AgentTrigger:
        """
        Fetch a trigger with its agent, workspace and service.

        :param trigger_id: The id of the trigger.
        :param base_queryset: The queryset to look the trigger up in, to add a lock
            or a filter. Defaults to the triggers that aren't trashed.
        :raises AgentTriggerDoesNotExist: When the trigger doesn't exist or is
            trashed.
        :return: The trigger.
        """

        queryset = (
            base_queryset if base_queryset is not None else AgentTrigger.objects.all()
        )
        try:
            return queryset.select_related("agent__workspace", "service").get(
                id=trigger_id
            )
        except AgentTrigger.DoesNotExist as exc:
            raise AgentTriggerDoesNotExist from exc

    def list_triggers(self, agent: AgentApplication) -> QuerySet[AgentTrigger]:
        """
        Return the agent's triggers with their services, oldest first.

        :param agent: The agent the triggers belong to.
        :return: The triggers that aren't trashed.
        """

        return AgentTrigger.objects.filter(agent=agent).select_related("service")

    def create_trigger(
        self,
        agent: AgentApplication,
        service_type: TriggerServiceTypeMixin,
        prepared_service_values: dict,
        message: str | BaserowFormulaObject = "",
        enabled: bool = True,
    ) -> AgentTrigger:
        """
        Create a trigger with a new service of the given type and arm it.

        :param agent: The agent the trigger starts conversations in.
        :param service_type: The trigger service type that produces the events.
        :param prepared_service_values: The service values, already passed through
            ``service_type.prepare_values``.
        :param message: The message formula resolved against the trigger payload.
        :param enabled: Whether firing starts a conversation.
        :return: The created trigger, with its specific service.
        """

        service = ServiceHandler().create_service(
            service_type, **prepared_service_values
        )
        trigger = AgentTrigger.objects.create(
            agent=agent, service=service, message=message, enabled=enabled
        )
        self.arm(trigger)
        return trigger

    def update_trigger(
        self,
        trigger: AgentTrigger,
        enabled: bool | None = None,
        message: str | BaserowFormulaObject | None = None,
        prepared_service_values: dict | None = None,
    ) -> AgentTrigger:
        """
        Update a trigger, re-arming its service when the service values changed
        or the trigger was switched on.

        :param trigger: The trigger to update.
        :param enabled: The new enabled state, or None to keep it.
        :param message: The new message formula, or None to keep it.
        :param prepared_service_values: The service values to set, already passed
            through ``prepare_values``, or None to leave the service as it is.
        :return: The updated trigger, with its specific service.
        """

        rearm = False
        if prepared_service_values is not None:
            service = trigger.service.specific
            updated = ServiceHandler().update_service(
                service.get_type(), service, **prepared_service_values
            )
            trigger.service = updated.service
            rearm = updated.original_service_values != updated.new_service_values
        changed_fields = []
        if enabled is not None and enabled != trigger.enabled:
            trigger.enabled = enabled
            changed_fields.append("enabled")
            rearm = rearm or enabled
        if message is not None:
            trigger.message = message
            changed_fields.append("message")
        if changed_fields:
            trigger.save(update_fields=[*changed_fields, "updated_on"])
        if rearm:
            self.arm(trigger)
        return trigger

    def delete_trigger(self, user: AbstractUser, trigger: AgentTrigger) -> None:
        """
        Trash a trigger; its service stops receiving events with it.

        :param user: The user deleting the trigger.
        :param trigger: The trigger to trash.
        """

        agent = trigger.agent
        TrashHandler.trash(user, agent.workspace, agent, trigger)

    def arm(self, trigger: AgentTrigger) -> None:
        """
        Make the trigger's service receive real events from now on.

        :param trigger: The trigger whose service is armed.
        """

        service = trigger.service.specific
        service.get_type().arm(service)
