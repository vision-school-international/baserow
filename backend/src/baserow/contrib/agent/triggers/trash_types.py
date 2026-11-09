from django.contrib.auth.models import AbstractUser

from baserow.contrib.agent.models import AgentApplication, AgentTrigger
from baserow.core.models import TrashEntry
from baserow.core.operations import UpdateApplicationOperationType
from baserow.core.trash.registries import TrashableItemType

from .handler import AgentTriggerHandler


class AgentTriggerTrashableItemType(TrashableItemType):
    """A trigger is trashed with its service, so no event reaches it meanwhile."""

    type = "agent_trigger"
    model_class = AgentTrigger

    def get_parent(self, trashed_item: AgentTrigger) -> AgentApplication:
        return trashed_item.agent

    def get_name(self, trashed_item: AgentTrigger) -> str:
        return trashed_item.service.get_type().type

    def trash(
        self,
        item_to_trash: AgentTrigger,
        requesting_user: AbstractUser,
        trash_entry: TrashEntry,
    ) -> None:
        super().trash(item_to_trash, requesting_user, trash_entry)
        self._set_service_trashed(item_to_trash, True)

    def restore(self, trashed_item: AgentTrigger, trash_entry: TrashEntry) -> None:
        super().restore(trashed_item, trash_entry)
        self._set_service_trashed(trashed_item, False)
        AgentTriggerHandler().arm(trashed_item)

    def permanently_delete_item(
        self, trashed_item: AgentTrigger, trash_item_lookup_cache: dict | None = None
    ) -> None:
        """The service goes with it through the trigger's ``post_delete`` receiver."""

        trashed_item.delete()

    def get_restore_operation_type(self) -> str:
        return UpdateApplicationOperationType.type

    def get_restore_operation_context(
        self, trash_entry: TrashEntry, trashed_item: AgentTrigger
    ) -> AgentApplication:
        return trashed_item.agent

    @staticmethod
    def _set_service_trashed(trigger: AgentTrigger, trashed: bool) -> None:
        """The due and webhook lookups skip trashed services without joining triggers."""

        service = trigger.service
        service.trashed = trashed
        service.save(update_fields=["trashed"])
