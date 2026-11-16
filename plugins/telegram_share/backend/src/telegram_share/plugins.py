from django.urls import include, path

from baserow.core.registries import Plugin


class TelegramSharePlugin(Plugin):
    """Mounts /api/share-cards/<slug>.png, like ai_tables' AITablesPlugin."""

    type = "telegram_share"

    def get_api_urls(self):
        from . import urls

        return [path("share-cards/", include(urls, namespace=self.type))]
