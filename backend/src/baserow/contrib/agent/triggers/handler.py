from zipfile import ZipFile

from django.contrib.auth.models import AbstractUser
from django.core.files.storage import Storage
from django.db.models import QuerySet

from baserow.contrib.agent.constants import (
    AGENT_TRIGGER_TYPES_ENABLED,
    AGENT_TRIGGER_TYPES_EXCLUDED,
)
from baserow.contrib.agent.models import AgentApplication, AgentTrigger
from baserow.core.formula.types import BaserowFormulaObject
from baserow.core.registries import ImportExportConfig
from baserow.core.services.handler import ServiceHandler
from baserow.core.services.registries import (
    TriggerServiceTypeMixin,
    service_type_registry,
)
from baserow.core.storage import ExportZipFile
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

    def available_trigger_types(self, agent: AgentApplication) -> list[str]:
        """
        List the trigger types a trigger of this Agent can have, in registry order.

        :param agent: The Agent the triggers would belong to.
        :return: The names of the registered trigger service types the picker
            allows, minus the ones deactivated in the Agent's workspace.
        """

        return [
            service_type.type
            for service_type in service_type_registry.get_all()
            if isinstance(service_type, TriggerServiceTypeMixin)
            and service_type.type in AGENT_TRIGGER_TYPES_ENABLED
            and service_type.type not in AGENT_TRIGGER_TYPES_EXCLUDED
            and not service_type.is_deactivated(agent.workspace)
        ]

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

    def export_triggers(
        self,
        agent: AgentApplication,
        import_export_config: ImportExportConfig | None = None,
        files_zip: ExportZipFile | None = None,
        storage: Storage | None = None,
        cache: dict | None = None,
    ) -> list[dict]:
        """
        Serialize the agent's triggers with their services.

        :param agent: The agent whose triggers are exported.
        :param import_export_config: How the agent is exported; it decides whether
            sensitive service values are redacted.
        :param files_zip: The zip file service files are written to.
        :param storage: The storage service files are read from.
        :param cache: A cache shared across the export.
        :return: The triggers, oldest first, each with its exported service.
        """

        service_handler = ServiceHandler()
        return [
            {
                "id": trigger.id,
                "enabled": trigger.enabled,
                "message": trigger.message,
                "service": service_handler.export_service(
                    trigger.service.specific,
                    import_export_config=import_export_config,
                    files_zip=files_zip,
                    storage=storage,
                    cache=cache,
                ),
            }
            for trigger in self.list_triggers(agent)
        ]

    def import_triggers(
        self,
        agent: AgentApplication,
        serialized_triggers: list[dict],
        id_mapping: dict,
        import_export_config: ImportExportConfig | None = None,
        files_zip: ZipFile | None = None,
        storage: Storage | None = None,
        cache: dict | None = None,
    ) -> list[AgentTrigger]:
        """
        Copy triggers into the agent, each switched off: a copy that fired on its
        own would run and bill without anyone asking for it, and a snapshot
        restore can't be told apart from a duplicate.

        :param agent: The agent the triggers are copied into.
        :param serialized_triggers: The triggers from ``export_triggers``.
        :param id_mapping: The export-to-import id map; ``agent_triggers`` and
            ``services`` are filled in.
        :param import_export_config: How the agent is imported.
        :param files_zip: The zip file service files are read from.
        :param storage: The storage service files are written to.
        :param cache: A cache shared across the import.
        :return: The created triggers, in the exported order.
        """

        trigger_ids = id_mapping.setdefault("agent_triggers", {})
        service_handler = ServiceHandler()
        triggers = []
        for serialized in serialized_triggers:
            service = service_handler.import_service(
                None,
                serialized["service"],
                id_mapping,
                files_zip=files_zip,
                storage=storage,
                cache=cache,
                import_export_config=import_export_config,
            )
            trigger = AgentTrigger.objects.create(
                agent=agent,
                service=service,
                enabled=False,
                message=serialized.get("message") or "",
            )
            trigger_ids[serialized["id"]] = trigger.id
            triggers.append(trigger)
        return triggers
