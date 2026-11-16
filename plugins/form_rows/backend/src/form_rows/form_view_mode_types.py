from baserow.contrib.database.views.registries import FormViewModeType


class FormWithRowsModeType(FormViewModeType):
    """
    The fields of a normal form plus a list of a view's rows. Core's form mode does
    nothing in its hooks either (views/form_view_mode_types.py); the list's
    settings are FormRowsSettings.
    """

    type = "form_with_rows"
