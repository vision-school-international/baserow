from typing import TYPE_CHECKING, Any, Dict, List

from rest_framework import serializers
from rest_framework.fields import SkipField

from baserow.api.generative_ai.errors import ERROR_MODEL_DOES_NOT_BELONG_TO_TYPE
from baserow.contrib.database.api.fields.errors import (
    ERROR_FIELD_NOT_IN_TABLE,
    ERROR_INCOMPATIBLE_FIELD,
)
from baserow.contrib.database.fields.dependencies.handler import (
    FieldDependencyHandler,
)
from baserow.contrib.database.fields.dependencies.models import FieldDependency
from baserow.contrib.database.fields.exceptions import (
    FieldNotInTable,
    IncompatibleField,
)
from baserow.contrib.database.fields.field_types import (
    LongTextFieldType,
    SingleSelectFieldType,
)
from baserow.contrib.database.fields.formula_visitors import (
    extract_field_id_dependencies,
)
from baserow.contrib.database.fields.models import Field, FileField
from baserow.contrib.database.fields.registries import field_type_registry
from baserow.contrib.database.formula_importer import import_formula
from baserow.core.ai_provider.constants import AI_PROVIDER_FEATURE_AI_FIELDS
from baserow.core.formula import BaserowFormulaException
from baserow.core.formula.serializers import FormulaSerializerField
from baserow.core.generative_ai.exceptions import ModelDoesNotBelongToType
from baserow.core.generative_ai.registries import generative_ai_model_type_registry

from .models import AIPromptChoiceField, AIPromptTextField

if TYPE_CHECKING:
    from baserow.contrib.database.fields.dependencies.update_collector import (
        DependencyContext,
    )


class PromptSerializerField(FormulaSerializerField):
    """
    Core's formula serializer field defaults a missing value to an empty formula.
    Field updates are validated non-partially, so that default would wipe the prompt
    whenever another property is updated. A missing prompt is left out instead.
    """

    def get_default(self):
        raise SkipField()


AI_SERIALIZER_FIELD_NAMES = [
    "ai_generative_ai_type",
    "ai_generative_ai_model",
    "ai_temperature",
    "ai_prompt",
    "ai_file_field_id",
    "ai_auto_update",
]
# `ai_auto_update_user_id` is set by the field type, never by a request; it must be
# allowed so `set_allowed_attrs` applies it on update.
AI_ALLOWED_FIELDS = AI_SERIALIZER_FIELD_NAMES + ["ai_auto_update_user_id"]
AI_SERIALIZER_FIELD_OVERRIDES = {
    "ai_generative_ai_type": serializers.CharField(
        required=False, allow_null=True, max_length=32
    ),
    "ai_generative_ai_model": serializers.CharField(
        required=False, allow_null=True, max_length=128
    ),
    "ai_temperature": serializers.FloatField(
        required=False, allow_null=True, min_value=0, max_value=2
    ),
    "ai_prompt": PromptSerializerField(
        required=False,
        help_text="The prompt run for each row. Can reference fields of the row.",
    ),
    "ai_file_field_id": serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="A file field whose attachments are sent to the model.",
    ),
    "ai_auto_update": serializers.BooleanField(
        required=False,
        help_text="Regenerate a row's cell when a referenced field changes.",
    ),
}
AI_API_EXCEPTIONS_MAP = {
    ModelDoesNotBelongToType: ERROR_MODEL_DOES_NOT_BELONG_TO_TYPE,
    FieldNotInTable: ERROR_FIELD_NOT_IN_TABLE,
    IncompatibleField: ERROR_INCOMPATIBLE_FIELD,
}


class AIPromptFieldTypeMixin:
    """
    The AI behaviour shared by both field types. Everything about the stored cell
    is inherited from the core type that comes after this mixin.
    """

    can_be_in_form_view = False
    keep_data_on_duplication = True

    # Matches the frontend's getCanBePrimaryField.
    def can_be_primary_field(self, field_or_values):
        return False

    # The core type whose view filters apply to this type.
    compatible_filter_type: str

    def get_compatible_filter_field_type(self, field):
        return field_type_registry.get(self.compatible_filter_type)

    def _validate_ai_values(self, table, values, current=None):
        """
        Raises when the selected model isn't enabled for AI fields in the workspace,
        or when the file field isn't a file field of the same table.

        :param table: The table the field is in.
        :param values: The values being set; missing keys fall back to `current`.
        :param current: The field before the update, when it already was this type.
        """

        def value(name):
            return values.get(name, getattr(current, name, None))

        ai_type = value("ai_generative_ai_type")
        ai_model = value("ai_generative_ai_model")
        enabled = generative_ai_model_type_registry.get_enabled_models_per_type(
            table.database.workspace, feature_type=AI_PROVIDER_FEATURE_AI_FIELDS
        )
        if not ai_type or ai_model not in enabled.get(ai_type, []):
            raise ModelDoesNotBelongToType(model_name=ai_model)

        file_field_id = value("ai_file_field_id")
        if file_field_id is not None:
            if not Field.objects.filter(id=file_field_id, table=table).exists():
                raise FieldNotInTable(
                    f"The field {file_field_id} is not in table {table.id}."
                )
            if not FileField.objects.filter(id=file_field_id).exists():
                raise IncompatibleField(f"The field {file_field_id} is not a file.")

    def before_create(
        self, table, primary, allowed_field_values, order, user, field_kwargs
    ):
        self._validate_ai_values(table, allowed_field_values)
        allowed_field_values["ai_auto_update_user_id"] = (
            user.id if user and allowed_field_values.get("ai_auto_update") else None
        )
        return super().before_create(
            table, primary, allowed_field_values, order, user, field_kwargs
        )

    def before_update(self, from_field, to_field_values, user, field_kwargs):
        current = from_field if isinstance(from_field, self.model_class) else None
        self._validate_ai_values(from_field.table, to_field_values, current)
        if "ai_auto_update" in to_field_values:
            enabling = to_field_values["ai_auto_update"]
            if not enabling:
                to_field_values["ai_auto_update_user_id"] = None
            elif not getattr(current, "ai_auto_update", False):
                # Whoever turns it on is who the generations run as.
                to_field_values["ai_auto_update_user_id"] = user.id if user else None
        return super().before_update(from_field, to_field_values, user, field_kwargs)

    def get_field_dependencies(self, field_instance, field_cache):
        try:
            field_ids = extract_field_id_dependencies(field_instance.ai_prompt)
        except BaserowFormulaException:
            field_ids = set()
        if field_instance.ai_file_field_id is not None:
            field_ids.add(field_instance.ai_file_field_id)
        # Never depend on itself: core rejects self references.
        field_ids.discard(field_instance.id)
        if not field_ids:
            return []

        referenced = Field.objects_and_trash.filter(
            id__in=field_ids, table_id=field_instance.table_id
        ).only("id", "name", "trashed")
        dependencies = []
        for field in referenced:
            if field.trashed:
                # Like formula fields, a trashed reference is kept by name so
                # restoring the field re-links it (update_fields_with_broken_references).
                dependencies.append(
                    FieldDependency(
                        dependant=field_instance,
                        broken_reference_field_name=field.name,
                    )
                )
            else:
                dependencies.append(
                    FieldDependency(dependant=field_instance, dependency_id=field.id)
                )
        return dependencies

    def _schedule_auto_update(self, field, starting_row, via_path, context):
        # Only direct changes in this table: deeper levels are reached when the
        # field in between changes its own cells.
        if context.depth != 0 or via_path or not field.ai_auto_update:
            return
        rows = starting_row if isinstance(starting_row, list) else [starting_row]
        from .tasks import schedule_auto_update

        schedule_auto_update(field.id, [row.id for row in rows])

    def row_of_dependency_created(
        self,
        field,
        starting_row,
        update_collector,
        field_cache,
        via_path_to_starting_table,
        dependency_context: "DependencyContext",
    ):
        self._schedule_auto_update(
            field, starting_row, via_path_to_starting_table, dependency_context
        )

    def row_of_dependency_updated(
        self,
        field,
        starting_row,
        update_collector,
        field_cache,
        via_path_to_starting_table,
        dependency_context: "DependencyContext",
    ):
        self._schedule_auto_update(
            field, starting_row, via_path_to_starting_table, dependency_context
        )

    def row_of_dependency_deleted(self, *args, **kwargs):
        # A deleted row has nothing left to generate.
        return

    def import_serialized(
        self,
        table,
        serialized_values: Dict[str, Any],
        import_export_config,
        id_mapping: Dict[str, Any],
        deferred_fk_update_collector,
    ):
        values = serialized_values.copy()
        # The file field may not exist yet; it's set once all fields are imported.
        file_field_id = values.pop("ai_file_field_id", None)
        if not import_export_config.is_duplicate:
            # The user may not exist, or be a member, where this is imported to.
            values["ai_auto_update"] = False
            values["ai_auto_update_user_id"] = None
        field = super().import_serialized(
            table,
            values,
            import_export_config,
            id_mapping,
            deferred_fk_update_collector,
        )
        if file_field_id is not None:
            deferred_fk_update_collector.add_deferred_fk_to_update(
                field, "ai_file_field_id", file_field_id, "database_fields"
            )
        return field

    def after_import_serialized(self, field, field_cache, id_mapping):
        # `get('fields.field_<old id>')` -> the id the field got on import.
        prompt = import_formula(field.ai_prompt, id_mapping)
        if prompt != field.ai_prompt:
            field.ai_prompt = prompt
            field.save(update_fields=["ai_prompt"])
        FieldDependencyHandler.rebuild_dependencies([field], field_cache)
        super().after_import_serialized(field, field_cache, id_mapping)


class AIPromptTextFieldType(AIPromptFieldTypeMixin, LongTextFieldType):
    type = "ai_prompt_text"
    model_class = AIPromptTextField
    compatible_filter_type = LongTextFieldType.type
    # Rich text is left out to keep v1 simple; the column stays False.
    allowed_fields = list(AI_ALLOWED_FIELDS)
    serializer_field_names = list(AI_SERIALIZER_FIELD_NAMES)
    serializer_field_overrides = AI_SERIALIZER_FIELD_OVERRIDES
    api_exceptions_map = {
        **LongTextFieldType.api_exceptions_map,
        **AI_API_EXCEPTIONS_MAP,
    }


class AIPromptChoiceFieldType(AIPromptFieldTypeMixin, SingleSelectFieldType):
    type = "ai_prompt_choice"
    model_class = AIPromptChoiceField
    compatible_filter_type = SingleSelectFieldType.type
    # No default option: the model picks the value.
    allowed_fields = ["select_options"] + AI_ALLOWED_FIELDS
    serializer_field_names = ["select_options"] + AI_SERIALIZER_FIELD_NAMES
    serializer_field_overrides = {
        "select_options": SingleSelectFieldType.serializer_field_overrides[
            "select_options"
        ],
        **AI_SERIALIZER_FIELD_OVERRIDES,
    }
    api_exceptions_map = {
        **SingleSelectFieldType.api_exceptions_map,
        **AI_API_EXCEPTIONS_MAP,
    }

    def get_default_options_field_name(self):
        # The column comes from the core single select model.
        return "single_select_default"


AI_PROMPT_FIELD_TYPES: List[type] = [AIPromptTextFieldType, AIPromptChoiceFieldType]


def get_options_by_value(field) -> Dict[str, Any]:
    """Maps option values to options, first one wins on duplicate values."""

    options = {}
    for option in field.select_options.all():
        options.setdefault(option.value, option)
    return options
