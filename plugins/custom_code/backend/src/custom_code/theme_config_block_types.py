from django.core.validators import URLValidator

from rest_framework import serializers

from baserow.contrib.builder.theme.registries import ThemeConfigBlockType

from .models import MAX_ASSETS, MAX_CODE_LENGTH, CustomCodeThemeConfigBlock

ASSET_STYLESHEET = "stylesheet"
ASSET_SCRIPT = "script"


class CustomAssetSerializer(serializers.Serializer):
    """An external stylesheet or script, loaded from its URL."""

    type = serializers.ChoiceField(choices=[ASSET_STYLESHEET, ASSET_SCRIPT])
    url = serializers.CharField(
        max_length=2000, validators=[URLValidator(schemes=["http", "https"])]
    )
    # Scripts only: how the browser runs it while the page loads.
    load = serializers.ChoiceField(
        choices=["", "defer", "async"], default="", required=False
    )
    # The HTML attribute value; "" leaves it out.
    crossorigin = serializers.ChoiceField(
        choices=["", "anonymous", "use-credentials"], default="", required=False
    )


class CustomCodeThemeConfigBlockType(ThemeConfigBlockType):
    type = "custom_code"
    model_class = CustomCodeThemeConfigBlock

    @property
    def serializer_field_overrides(self):
        def help_text(name):
            return self.model_class._meta.get_field(name).help_text

        return {
            **{
                name: serializers.CharField(
                    allow_blank=True,
                    required=False,
                    max_length=MAX_CODE_LENGTH,
                    help_text=help_text(name),
                )
                for name in ("custom_css", "custom_js")
            },
            "custom_assets": serializers.ListField(
                child=CustomAssetSerializer(),
                required=False,
                max_length=MAX_ASSETS,
                help_text=help_text("custom_assets"),
            ),
        }

    def import_serialized(
        self,
        parent,
        serialized_values,
        id_mapping,
        files_zip=None,
        storage=None,
        cache=None,
        **kwargs,
    ):
        """
        Imported code is reported like the builder's other active content, so an
        application imported from outside stays untrusted, and its code off, until
        its owner reviews it (core/import_export/untrusted_content.py).
        """

        instance = super().import_serialized(
            parent, serialized_values, id_mapping, files_zip, storage, cache, **kwargs
        )
        if cache is not None:
            report = cache.setdefault("import_report", [])
            if instance.custom_css:
                report.append({"type": "custom_css"})
            if instance.custom_js:
                report.append({"type": "custom_js"})
            for asset in instance.custom_assets:
                report.append(
                    {
                        "type": "external_stylesheet"
                        if asset.get("type") == ASSET_STYLESHEET
                        else "external_script",
                        "url": asset.get("url", ""),
                    }
                )
        return instance
