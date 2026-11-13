from django.conf import settings

from rest_framework import serializers

from baserow.api.errors import ERROR_GROUP_DOES_NOT_EXIST, ERROR_USER_NOT_IN_GROUP
from baserow.api.generative_ai.errors import ERROR_MODEL_DOES_NOT_BELONG_TO_TYPE
from baserow.contrib.database.api.fields.errors import (
    ERROR_FIELD_DOES_NOT_EXIST,
    ERROR_INCOMPATIBLE_FIELD,
)
from baserow.contrib.database.api.rows.errors import ERROR_ROW_DOES_NOT_EXIST
from baserow.contrib.database.api.views.errors import ERROR_VIEW_DOES_NOT_EXIST
from baserow.contrib.database.fields.exceptions import (
    FieldDoesNotExist,
    IncompatibleField,
)
from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.fields.registries import field_type_registry
from baserow.contrib.database.rows.exceptions import RowDoesNotExist
from baserow.contrib.database.rows.handler import RowHandler
from baserow.contrib.database.rows.operations import UpdateDatabaseRowOperationType
from baserow.contrib.database.views.exceptions import ViewDoesNotExist
from baserow.contrib.database.views.handler import ViewHandler
from baserow.core.ai_provider.constants import AI_PROVIDER_FEATURE_AI_FIELDS
from baserow.core.exceptions import UserNotInWorkspace, WorkspaceDoesNotExist
from baserow.core.generative_ai.exceptions import ModelDoesNotBelongToType
from baserow.core.generative_ai.registries import generative_ai_model_type_registry
from baserow.core.handler import CoreHandler
from baserow.core.job_types import _empty_transaction_context
from baserow.core.jobs.exceptions import MaxJobCountExceeded
from baserow.core.jobs.registries import JobType
from baserow.core.utils import ChildProgressBuilder

from .handler import AIPromptHandler
from .models import GenerateAIPromptValuesJob, TransformAICellsJob

TRANSFORMABLE_FIELD_TYPES = ("text", "long_text")


class GenerateAIPromptValuesJobType(JobType):
    type = "generate_ai_prompt_values"
    model_class = GenerateAIPromptValuesJob
    # Applies to whole view/table runs only; see `_can_schedule_or_raise`.
    max_count = 3

    api_exceptions_map = {
        UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
        WorkspaceDoesNotExist: ERROR_GROUP_DOES_NOT_EXIST,
        FieldDoesNotExist: ERROR_FIELD_DOES_NOT_EXIST,
        ViewDoesNotExist: ERROR_VIEW_DOES_NOT_EXIST,
        RowDoesNotExist: ERROR_ROW_DOES_NOT_EXIST,
        ModelDoesNotBelongToType: ERROR_MODEL_DOES_NOT_BELONG_TO_TYPE,
    }
    serializer_field_names = ["field_id", "row_ids", "view_id", "only_empty"]
    serializer_field_overrides = {
        "field_id": serializers.IntegerField(
            help_text="The AI prompt field to generate values for."
        ),
        "row_ids": serializers.ListField(
            child=serializers.IntegerField(),
            required=False,
            min_length=1,
            max_length=settings.BATCH_ROWS_SIZE_LIMIT,
            help_text="Only generate these rows.",
        ),
        "view_id": serializers.IntegerField(
            required=False,
            help_text="Without row ids, only generate the rows visible in this view. "
            "Without both, every row of the table is generated.",
        ),
        "only_empty": serializers.BooleanField(
            required=False,
            default=False,
            help_text="Only generate cells that are empty.",
        ),
    }

    def _can_schedule_or_raise(self, running_jobs, job):
        # Selected rows are bounded by the batch limit, so they aren't capped.
        if job.row_ids:
            return
        whole_runs = [j for j in running_jobs if not j.row_ids]
        super()._can_schedule_or_raise(whole_runs, job)
        if any(j.field_id == job.field_id for j in whole_runs):
            raise MaxJobCountExceeded(
                f"Only one {self.type} job can run at the same time per field."
            )

    def transaction_atomic_context(self, job):
        # Rows are saved chunk by chunk so users see values as they arrive.
        return _empty_transaction_context()

    def _get_field_or_raise(self, field_id):
        field = AIPromptHandler().get_field(field_id)
        if field is None:
            raise FieldDoesNotExist(f"The field {field_id} is not an AI prompt field.")
        return field

    def prepare_values(self, values, user):
        field = self._get_field_or_raise(values["field_id"])
        table = field.table
        CoreHandler().check_permissions(
            user,
            UpdateDatabaseRowOperationType.type,
            workspace=table.database.workspace,
            context=table,
        )
        enabled = generative_ai_model_type_registry.get_enabled_models_per_type(
            table.database.workspace, feature_type=AI_PROVIDER_FEATURE_AI_FIELDS
        )
        if field.ai_generative_ai_model not in enabled.get(
            field.ai_generative_ai_type, []
        ):
            raise ModelDoesNotBelongToType(model_name=field.ai_generative_ai_model)

        prepared = {"field": field, "only_empty": values.get("only_empty", False)}
        row_ids = values.get("row_ids")
        view_id = values.get("view_id")
        if row_ids:
            row_ids = list(dict.fromkeys(row_ids))
            found = set(
                RowHandler()
                .get_rows(table.get_model(), row_ids)
                .values_list("id", flat=True)
            )
            missing = sorted(set(row_ids) - found)
            if missing:
                raise RowDoesNotExist(missing)
            prepared["row_ids"] = row_ids
        elif view_id is not None:
            prepared["view"] = ViewHandler().get_view_as_user(
                user, view_id, table_id=table.id
            )
        return prepared

    def run(self, job, progress):
        field = self._get_field_or_raise(job.field_id)
        table = field.table
        CoreHandler().check_permissions(
            job.user,
            UpdateDatabaseRowOperationType.type,
            workspace=table.database.workspace,
            context=table,
        )
        model = table.get_model()
        if job.row_ids:
            rows = RowHandler().get_rows(model, job.row_ids)
        elif job.view_id is not None:
            view_handler = ViewHandler()
            view = view_handler.get_view_as_user(
                job.user, job.view_id, table_id=table.id
            )
            rows = view_handler.get_queryset(job.user, view, model=model)
        else:
            rows = model.objects.all()

        if job.only_empty:
            model_field = model._meta.get_field(field.db_column)
            rows = rows.filter(
                field.get_type().empty_query(field.db_column, model_field, field)
            )

        row_ids = list(rows.values_list("id", flat=True))
        rows_progress = ChildProgressBuilder.build(
            progress.create_child_builder(represents_progress=progress.total),
            max(1, len(row_ids)),
        )
        AIPromptHandler().generate_values(
            job.user, field, row_ids, progress=rows_progress, signal_sender=self
        )
        if not row_ids:
            rows_progress.increment()


class TransformAICellsJobType(JobType):
    """Rewrites the selected cells of a text field in place with an instruction."""

    type = "transform_ai_cells"
    model_class = TransformAICellsJob
    max_count = 3

    api_exceptions_map = {
        UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
        WorkspaceDoesNotExist: ERROR_GROUP_DOES_NOT_EXIST,
        FieldDoesNotExist: ERROR_FIELD_DOES_NOT_EXIST,
        IncompatibleField: ERROR_INCOMPATIBLE_FIELD,
        RowDoesNotExist: ERROR_ROW_DOES_NOT_EXIST,
        ModelDoesNotBelongToType: ERROR_MODEL_DOES_NOT_BELONG_TO_TYPE,
    }
    request_serializer_field_names = [
        "field_id",
        "row_ids",
        "instruction",
        "ai_generative_ai_type",
        "ai_generative_ai_model",
        "ai_temperature",
    ]
    request_serializer_field_overrides = {
        "field_id": serializers.IntegerField(
            help_text="The text or long text field whose cells are rewritten."
        ),
        "row_ids": serializers.ListField(
            child=serializers.IntegerField(),
            min_length=1,
            max_length=settings.BATCH_ROWS_SIZE_LIMIT,
            help_text="The rows whose cell is rewritten.",
        ),
        "instruction": serializers.CharField(
            max_length=2000, help_text="What the model does with every cell."
        ),
        "ai_generative_ai_type": serializers.CharField(max_length=32),
        "ai_generative_ai_model": serializers.CharField(max_length=128),
        "ai_temperature": serializers.FloatField(
            required=False, allow_null=True, min_value=0, max_value=2
        ),
    }
    serializer_field_names = request_serializer_field_names + ["failed_row_ids"]
    serializer_field_overrides = {
        **request_serializer_field_overrides,
        "failed_row_ids": serializers.ListField(
            child=serializers.IntegerField(),
            help_text="The rows left unchanged: the model failed on them, or their "
            "cell was edited while the model ran.",
        ),
    }

    def transaction_atomic_context(self, job):
        # The model calls run outside a transaction; the save opens its own.
        return _empty_transaction_context()

    def _get_field_or_raise(self, user, field_id):
        """The writable text field, if the user may update rows of its table."""

        field = FieldHandler().get_field(field_id).specific
        if (
            field_type_registry.get_by_model(field).type
            not in TRANSFORMABLE_FIELD_TYPES
            or field.read_only
        ):
            raise IncompatibleField("Only writable text fields can be transformed.")
        table = field.table
        CoreHandler().check_permissions(
            user,
            UpdateDatabaseRowOperationType.type,
            workspace=table.database.workspace,
            context=table,
        )
        return field

    def prepare_values(self, values, user):
        field = self._get_field_or_raise(user, values["field_id"])
        table = field.table
        enabled = generative_ai_model_type_registry.get_enabled_models_per_type(
            table.database.workspace, feature_type=AI_PROVIDER_FEATURE_AI_FIELDS
        )
        if values["ai_generative_ai_model"] not in enabled.get(
            values["ai_generative_ai_type"], []
        ):
            raise ModelDoesNotBelongToType(model_name=values["ai_generative_ai_model"])

        row_ids = list(dict.fromkeys(values["row_ids"]))
        found = set(
            table.get_model()
            .objects.filter(id__in=row_ids)
            .values_list("id", flat=True)
        )
        missing = sorted(set(row_ids) - found)
        if missing:
            raise RowDoesNotExist(missing)
        return {
            "field": field,
            "row_ids": row_ids,
            "instruction": values["instruction"],
            "ai_generative_ai_type": values["ai_generative_ai_type"],
            "ai_generative_ai_model": values["ai_generative_ai_model"],
            "ai_temperature": values.get("ai_temperature"),
        }

    def run(self, job, progress):
        # Checked again: the field or the user's access may have changed.
        field = self._get_field_or_raise(job.user, job.field_id)
        rows_progress = ChildProgressBuilder.build(
            progress.create_child_builder(represents_progress=progress.total),
            len(job.row_ids),
        )
        # Saved with the finished state by run_async_job (core/jobs/tasks.py).
        job.failed_row_ids = AIPromptHandler().transform_cells(
            job, field, progress=rows_progress
        )
