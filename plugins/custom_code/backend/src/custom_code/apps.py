from django.apps import AppConfig


class CustomCodeConfig(AppConfig):
    name = "custom_code"

    def ready(self):
        # Same registration as core's theme blocks (contrib/builder/apps.py).
        from baserow.contrib.builder.theme.registries import (
            theme_config_block_registry,
        )

        from .theme_config_block_types import CustomCodeThemeConfigBlockType

        theme_config_block_registry.register(CustomCodeThemeConfigBlockType())
