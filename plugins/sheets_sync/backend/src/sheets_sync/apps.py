from django.apps import AppConfig


class SheetsSyncConfig(AppConfig):
    name = "sheets_sync"

    def ready(self):
        # Same registration as core (contrib/database/apps.py:849-850).
        from baserow.contrib.database.data_sync.registries import (
            data_sync_type_registry,
            two_way_sync_strategy_type_registry,
        )

        from .data_sync_types import GoogleSheetsDataSyncType
        from .strategy import GoogleSheetsPushStrategy

        data_sync_type_registry.register(GoogleSheetsDataSyncType())
        two_way_sync_strategy_type_registry.register(GoogleSheetsPushStrategy())

        # Connects the receivers, as core does (contrib/database/apps.py:1385-1387).
        import sheets_sync.receivers  # noqa: F401
