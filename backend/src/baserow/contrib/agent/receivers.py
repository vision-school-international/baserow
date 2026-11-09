from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from baserow.contrib.agent.last_viewed_types import AgentLastViewedItemType
from baserow.contrib.agent.models import AgentConversation
from baserow.contrib.agent.signals import agent_loaded
from baserow.contrib.agent.trash_types import AgentConversationTrashableItemType
from baserow.core.last_viewed.handler import LastViewedHandler
from baserow.core.models import TrashEntry

User = get_user_model()


@receiver(agent_loaded)
def agent_loaded_mark_last_viewed(
    sender, agent_id: int, user: AbstractUser, **kwargs
) -> None:
    LastViewedHandler.schedule_mark_viewed(user, AgentLastViewedItemType.type, agent_id)


@receiver(pre_delete, sender=User)
def delete_owned_conversations(sender, instance: AbstractUser, **kwargs) -> None:
    """
    Removes the user's conversations; without their owner, trash entries would
    show private titles to everyone, and a nullable owner no longer orders the
    cascade before the user row.
    """

    AgentConversation.objects_and_trash.filter(owner_user=instance).delete()
    TrashEntry.objects.filter(
        trash_item_type=AgentConversationTrashableItemType.type,
        trash_item_owner=instance,
    ).delete()
