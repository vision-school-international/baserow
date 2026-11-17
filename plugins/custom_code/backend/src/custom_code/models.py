from django.db import models

from baserow.contrib.builder.theme.models import ThemeConfigBlock

# Enough for a full stylesheet or script, small enough to keep the builder payload sane.
MAX_CODE_LENGTH = 200_000
MAX_ASSETS = 50


class CustomCodeThemeConfigBlock(ThemeConfigBlock):
    """
    The application's own CSS, JavaScript and external assets. As a theme block it's
    serialized, exported, imported and duplicated with the rest of the theme, and
    reaches the published site through the public builder's theme.
    """

    custom_css = models.TextField(
        blank=True,
        default="",
        db_default="",
        help_text="CSS added to every page of the application.",
    )
    custom_js = models.TextField(
        blank=True,
        default="",
        db_default="",
        help_text="JavaScript run on every page of the published application.",
    )
    # Like ColorThemeConfigBlock.custom_colors. Validated by its serializer
    # (theme_config_block_types.CustomAssetSerializer).
    custom_assets = models.JSONField(
        default=list,
        db_default=[],
        help_text="External stylesheets and scripts, in loading order: objects with "
        "a type, url, load and crossorigin.",
    )
