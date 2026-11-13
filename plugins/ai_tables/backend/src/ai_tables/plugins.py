from django.urls import include, path

from baserow.core.registries import Plugin


class AITablesPlugin(Plugin):
    """Mounts the plugin's API under /api/ai-tables/ (core/registries.py Plugin)."""

    type = "ai_tables"

    def get_api_urls(self):
        from . import urls

        return [path("ai-tables/", include(urls, namespace=self.type))]
