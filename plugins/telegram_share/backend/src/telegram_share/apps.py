from django.apps import AppConfig


class TelegramShareConfig(AppConfig):
    name = "telegram_share"

    def ready(self):
        # Same registration as core (contrib/database/apps.py).
        from baserow.contrib.database.workflow_actions.registries import (
            database_workflow_action_type_registry,
        )
        from baserow.core.registries import plugin_registry

        from .plugins import TelegramSharePlugin
        from .workflow_action_types import TelegramSendWorkflowActionType

        database_workflow_action_type_registry.register(
            TelegramSendWorkflowActionType()
        )
        plugin_registry.register(TelegramSharePlugin())
