from django.apps import AppConfig


class FormRowsConfig(AppConfig):
    name = "form_rows"

    def ready(self):
        # Same registration as core (contrib/database/apps.py).
        from baserow.contrib.database.views.registries import form_view_mode_registry
        from baserow.core.registries import plugin_registry

        from .form_view_mode_types import FormWithRowsModeType
        from .plugins import FormRowsPlugin

        form_view_mode_registry.register(FormWithRowsModeType())
        plugin_registry.register(FormRowsPlugin())
