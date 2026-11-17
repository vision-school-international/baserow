import json
from typing import Annotated, Any

from pydantic import Field

from baserow.contrib.builder.api.theme.serializers import serialize_builder_theme
from baserow.contrib.builder.theme.service import ThemeService
from baserow.contrib.builder.tools.lookups import get_builder_in_workspace
from baserow.core.tools import ToolContext
from baserow.core.tools.errors import ToolInputError

BuilderId = Annotated[
    int, Field(description="The ID of the application builder, from list_builders.")
]


def get_theme(ctx: ToolContext, builder_id: BuilderId) -> dict[str, Any]:
    """
    Get every theme setting of an application builder, by name: colors, typography,
    buttons, links, images, inputs, tables and the application's custom code
    (custom_css, custom_js, and custom_assets, the external stylesheets and scripts).
    Read it before styling elements so their styles don't fight the theme.
    """

    # Checks the application is in the workspace and visible to the user.
    builder = get_builder_in_workspace(ctx, builder_id)
    return serialize_builder_theme(builder)


def update_theme(
    ctx: ToolContext,
    builder_id: BuilderId,
    values: Annotated[
        dict[str, Any],
        Field(
            description="The theme settings to change, by the names get_theme "
            "returns. Settings left out keep their value."
        ),
    ],
) -> dict[str, Any]:
    """
    Change some theme settings of an application builder, such as one color or the
    custom CSS, without touching the rest. Values are checked like in the theme
    editor. custom_js and script assets only run on the published site.
    """

    # Imported here: built while apps start, it would miss plugin theme blocks
    # (builder/api/theme/serializers.py `__getattr__`).
    from baserow.contrib.builder.api.theme.serializers import (
        CombinedThemeConfigBlocksRequestSerializer,
    )

    builder = get_builder_in_workspace(ctx, builder_id)
    # The same validation as the theme API (builder/api/theme/views.py ThemeView).
    serializer = CombinedThemeConfigBlocksRequestSerializer(data=values, partial=True)
    if not serializer.is_valid():
        # DRF's error details are strs, so they dump as plain messages.
        raise ToolInputError(f"Invalid theme settings: {json.dumps(serializer.errors)}")
    unknown = set(values) - set(serializer.validated_data)
    if unknown:
        raise ToolInputError(
            f"Unknown theme settings: {', '.join(sorted(unknown))}.",
            hint="Use the names get_theme returns.",
        )

    ctx.update_status(f"Updating the theme of {builder.name}...")
    # Checks the user may update the theme, and tells open editors.
    ThemeService().update_theme(ctx.user, builder, **serializer.validated_data)
    return {"updated": sorted(serializer.validated_data)}
