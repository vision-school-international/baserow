from django.db import models

from baserow.contrib.database.fields.models import FormViewEditRowField
from baserow.contrib.database.views.models import FormView, View


class FormRowsSettings(models.Model):
    """The settings of a form in the "Form with existing rows" mode."""

    form_view = models.OneToOneField(
        FormView, on_delete=models.CASCADE, related_name="form_rows_settings"
    )
    list_view = models.ForeignKey(
        View,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="The view of the form's table whose rows are listed.",
    )
    heading = models.CharField(max_length=255, blank=True, default="")
    intro = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="The line under the heading.",
    )
    allow_edit = models.BooleanField(
        default=False,
        help_text="Show an Edit button on every listed row. Anyone with the form's "
        "link can then change any listed row.",
    )
    edit_field = models.ForeignKey(
        FormViewEditRowField,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="The edit link field whose per-row links the Edit buttons open.",
    )
