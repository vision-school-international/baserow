from django.db import models

from baserow.contrib.database.views.models import FormView, FormViewFieldOptions
from baserow.contrib.database.workflow_actions.models import OpenUrlWorkflowAction
from baserow.core.formula.field import FormulaField as CoreFormulaModelField


class TelegramSendWorkflowAction(OpenUrlWorkflowAction):
    """
    Opens a Telegram chat with the row's contact, with a message and a form link
    typed in. A subclass of the open URL action, so the button opens its new tab
    on click like one (`ButtonField.opens_new_tab`).
    """

    recipient = CoreFormulaModelField(
        default="",
        db_default="",
        help_text="The Telegram username to write to, as a formula.",
    )
    message = CoreFormulaModelField(
        default="",
        db_default="",
        help_text="The message typed into the chat, as a formula.",
    )
    form_view = models.ForeignKey(
        FormView,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="A form of the button's table to link at the end of the message.",
    )
    prefill = models.BooleanField(
        default=False,
        db_default=False,
        help_text="Fill the linked form with the clicked row's values.",
    )

    @property
    def form(self):
        """What the browser needs to link the form, or None without one."""

        view = self.form_view
        if view is None or view.trashed:
            return None
        return {
            "slug": str(view.slug),
            "public": view.public,
            # The default manager leaves out trashed fields.
            "field_ids": list(
                FormViewFieldOptions.objects.filter(
                    form_view=view, enabled=True
                ).values_list("field_id", flat=True)
            ),
        }
