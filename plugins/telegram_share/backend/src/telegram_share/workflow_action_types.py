from typing import Any, Dict, Optional
from zipfile import ZipFile

from django.contrib.auth.models import AbstractUser
from django.core.files.storage import Storage

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from baserow.contrib.database.views.models import FormView
from baserow.contrib.database.workflow_actions.types import DatabaseWorkflowActionDict
from baserow.contrib.database.workflow_actions.workflow_action_types import (
    OpenUrlWorkflowActionType,
)
from baserow.core.deferred_callbacks import register_deferred_callback
from baserow.core.formula.serializers import FormulaSerializerField
from baserow.core.workflow_actions.models import WorkflowAction

from .models import TelegramSendWorkflowAction


class TelegramSendWorkflowActionType(OpenUrlWorkflowActionType):
    """
    Opens `t.me/<username>?text=<message>` in the clicker's browser, so their own
    Telegram writes to the row's contact. Frontend-only, like the open URL action
    it extends; the browser builds the link (telegramShare/workflowActionTypes.js).
    """

    type = "telegram_send"
    model_class = TelegramSendWorkflowAction

    allowed_fields = OpenUrlWorkflowActionType.allowed_fields + [
        "recipient",
        "message",
        "form_view_id",
        "prefill",
    ]
    serializer_field_names = ["recipient", "message", "form_view_id", "prefill", "form"]
    simple_formula_fields = ["recipient", "message"]
    serializer_field_overrides = {
        "recipient": FormulaSerializerField(
            help_text="The Telegram username to write to, as a formula.",
            required=False,
        ),
        "message": FormulaSerializerField(
            help_text="The message typed into the chat, as a formula.",
            required=False,
        ),
        "form_view_id": serializers.IntegerField(
            help_text="A form of the button's table to link in the message.",
            required=False,
            allow_null=True,
        ),
        "prefill": serializers.BooleanField(
            help_text="Fill the linked form with the clicked row's values.",
            required=False,
        ),
        "form": serializers.JSONField(
            help_text="The linked form's slug, whether it's public and its fields.",
            read_only=True,
        ),
    }

    class SerializedDict(DatabaseWorkflowActionDict):
        recipient: str
        message: str
        form_view_id: Optional[int]
        prefill: bool
        target: str

    def prepare_values(
        self,
        values: Dict[str, Any],
        user: AbstractUser,
        instance: Optional[WorkflowAction] = None,
    ) -> Dict[str, Any]:
        # Always a new tab: Telegram's page would replace the table otherwise.
        values["target"] = "blank"

        form_view_id = values.get("form_view_id")
        if form_view_id is not None:
            # The field is in the values on create (the base pops it).
            field = values.get("field") or instance.field
            # Only a form of the button's own table: the slug is handed to every
            # clicker, so another table's form would leak. A trashed one is kept,
            # so other edits still save; `form` hides it until it's restored.
            if not FormView.objects_and_trash.filter(
                id=form_view_id, table_id=field.table_id
            ).exists():
                raise ValidationError(
                    {"form_view_id": "Pick a form of this button's table."}
                )

        return super().prepare_values(values, user, instance)

    def deserialize_property(
        self,
        prop_name: str,
        value: Any,
        id_mapping: Dict[str, Dict[int, int]],
        files_zip: Optional[ZipFile] = None,
        storage: Optional[Storage] = None,
        cache: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        # Set once the views exist, see `import_serialized`.
        if prop_name == "form_view_id":
            return None
        return super().deserialize_property(
            prop_name, value, id_mapping, files_zip, storage, cache, **kwargs
        )

    def import_serialized(
        self,
        parent: Any,
        serialized_values: Dict[str, Any],
        id_mapping: Dict[str, Dict[int, int]],
        files_zip: Optional[ZipFile] = None,
        storage: Optional[Storage] = None,
        cache: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> WorkflowAction:
        """
        Imports the action, then points it at the imported copy of its form. The
        views are imported after the fields, so this waits for the end of the
        import, like the base's formula remapping.
        """

        created = super().import_serialized(
            parent,
            serialized_values,
            id_mapping,
            files_zip,
            storage,
            cache,
            **kwargs,
        )
        old_form_view_id = serialized_values.get("form_view_id")
        if not old_form_view_id:
            return created

        def import_form_view():
            new_id = id_mapping.get("database_views", {}).get(old_form_view_id)
            # A copy of the button inside the same table, a duplicated field for
            # instance, keeps the form it had.
            if (
                new_id is None
                and FormView.objects_and_trash.filter(
                    id=old_form_view_id, table_id=created.field.table_id
                ).exists()
            ):
                new_id = old_form_view_id
            if new_id is not None:
                created.form_view_id = new_id
                created.save(update_fields=["form_view"])

        register_deferred_callback(import_form_view)
        return created
