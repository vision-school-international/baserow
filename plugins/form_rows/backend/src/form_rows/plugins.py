from django.urls import include, path

from baserow.core.registries import Plugin


class FormRowsPlugin(Plugin):
    """Mounts /api/form-rows/, like ai_tables' AITablesPlugin."""

    type = "form_rows"

    def get_api_urls(self):
        from . import urls

        return [path("form-rows/", include(urls, namespace=self.type))]
