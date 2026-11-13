from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

from django.conf import settings
from django.db import connections, transaction

from loguru import logger

from baserow.contrib.database.fields.exceptions import FieldDoesNotExist
from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.rows.actions import UpdateRowsActionType
from baserow.contrib.database.rows.exceptions import RowDoesNotExist
from baserow.contrib.database.rows.handler import RowHandler
from baserow.contrib.database.rows.operations import UpdateDatabaseRowOperationType
from baserow.contrib.database.rows.runtime_formula_contexts import (
    HumanReadableRowContext,
)
from baserow.contrib.database.rows.signals import rows_ai_values_generation_error
from baserow.core.action.registries import action_type_registry
from baserow.core.formula import resolve_formula
from baserow.core.formula.registries import formula_runtime_function_registry
from baserow.core.formula.types import BaserowFormulaObject
from baserow.core.generative_ai.exceptions import (
    GenerativeAIPromptError,
    get_user_friendly_error_message,
)
from baserow.core.generative_ai.registries import generative_ai_model_type_registry
from baserow.core.handler import CoreHandler
from baserow.core.storage import get_default_storage
from baserow.core.user_files.handler import UserFileHandler
from baserow.core.utils import Progress, grouper

from .field_types import get_options_by_value
from .models import AI_PROMPT_FIELD_MODELS, AIPromptChoiceField


@dataclass
class AIFile:
    """
    A file handed to a provider's FileHandler. Exactly the attributes core's
    FileHandler reads (baserow/core/generative_ai/registries.py).
    """

    name: str
    original_name: str
    size: int
    mime_type: str
    content: Any = None
    provider_file_id: Optional[str] = None

    def read_content(self) -> bytes:
        path = UserFileHandler().user_file_path(self.name)
        with get_default_storage().open(path) as file:
            return file.read()


class RowGenerationError(Exception):
    """A row whose value can't be generated; the run continues with the others."""


# The answer replaces the cell, so the model must return the new text only.
TRANSFORM_PROMPT = (
    "{instruction}\n\n"
    "Apply the instruction above to the text below. Reply with only the "
    "resulting text, without quotes or explanation.\n\n"
    "Text:\n{text}"
)


class AIPromptHandler:
    def get_field(self, field_id: int):
        """
        Returns the specific AI prompt field, or None if it's gone, trashed, or of
        another type.
        """

        try:
            # Also raises when the table, database or workspace is trashed.
            field = FieldHandler().get_field(field_id).specific
        except FieldDoesNotExist:
            return None
        return field if isinstance(field, AI_PROMPT_FIELD_MODELS) else None

    def build_prompt(self, field, row) -> str:
        """
        Resolves the prompt against the human readable values of the row, without
        the field's own value.
        """

        value = resolve_formula(
            BaserowFormulaObject.to_formula(field.ai_prompt),
            formula_runtime_function_registry,
            HumanReadableRowContext(row, exclude_field_ids=[field.id]),
        )
        return "" if value is None else str(value)

    def get_files(self, field, row) -> List[AIFile]:
        file_field_id = field.ai_file_field_id
        if file_field_id is None:
            return []
        # A trashed file field isn't in the model, so it simply sends nothing.
        field_object = row._meta.model._field_objects.get(file_field_id)
        if field_object is None:
            return []
        return [
            AIFile(
                name=file["name"],
                original_name=file.get("visible_name") or file["name"],
                size=file["size"],
                mime_type=file["mime_type"],
            )
            for file in getattr(row, field_object["name"]) or []
        ]

    def _prompt_model(
        self, model_type, model, temperature, workspace, prompt, files, output
    ):
        """
        Runs in a worker thread. It touches the database only through the provider
        settings lookup, so it closes this thread's connections when done.
        """

        try:
            prepared = []
            if files and model_type.supports_files:
                prepared = model_type.prepare_files(files, workspace=workspace)
            try:
                return model_type.prompt(
                    model,
                    prompt,
                    workspace=workspace,
                    temperature=temperature,
                    output_type=output,
                    content=[f.content for f in prepared] or None,
                )
            finally:
                if prepared:
                    model_type.cleanup_files(prepared, workspace=workspace)
        finally:
            connections.close_all()

    def _to_cell_value(self, field, answer, options_by_value):
        if isinstance(field, AIPromptChoiceField):
            option = options_by_value.get(answer)
            if option is None:
                raise RowGenerationError("The answer matched none of the options.")
            return option.id
        text = "" if answer is None else str(answer)
        return text[: settings.MAX_FIELD_TEXT_LENGTH]

    def _save(self, user, table, model, values: List[dict]):
        try:
            RowHandler().update_rows(user, table, values, model=model)
        except RowDoesNotExist as exc:
            # Rows deleted while generating are skipped.
            missing = set(exc.ids)
            values = [v for v in values if v["id"] not in missing]
            if values:
                RowHandler().update_rows(user, table, values, model=model)

    def generate_values(
        self,
        user,
        field,
        row_ids: Iterable[int],
        progress: Optional[Progress] = None,
        signal_sender: Any = None,
    ) -> dict[int, str]:
        """
        Generates and saves the cell of every given row. A row that fails is
        recorded and reported through `rows_ai_values_generation_error`, the others
        still get their value. Model calls run in threads; prompts are built and
        rows saved in this thread.

        :return: The error message per row id that failed.
        """

        table = field.table
        workspace = table.database.workspace
        model_type = generative_ai_model_type_registry.get(field.ai_generative_ai_type)
        model = table.get_model()
        options_by_value = (
            get_options_by_value(field)
            if isinstance(field, AIPromptChoiceField)
            else {}
        )
        output = list(options_by_value) if options_by_value else None
        errors: dict[int, str] = {}
        workers = max(1, settings.AI_TABLES_MAX_CONCURRENT_GENERATIONS)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            for chunk in grouper(workers * 2, row_ids):
                rows = model.objects.enhance_by_fields().filter(id__in=chunk)
                futures = {}
                for row in rows:
                    try:
                        if isinstance(field, AIPromptChoiceField) and not output:
                            raise RowGenerationError("The field has no options.")
                        prompt = self.build_prompt(field, row)
                        if not prompt.strip():
                            raise RowGenerationError("The prompt is empty.")
                        files = self.get_files(field, row)
                    except Exception as exc:
                        errors[row.id] = self._message(exc)
                        continue
                    future = executor.submit(
                        self._prompt_model,
                        model_type,
                        field.ai_generative_ai_model,
                        field.ai_temperature,
                        workspace,
                        prompt,
                        files,
                        output,
                    )
                    futures[future] = row

                values = []
                for future in as_completed(futures):
                    row = futures[future]
                    try:
                        cell = self._to_cell_value(
                            field, future.result(), options_by_value
                        )
                        values.append({"id": row.id, f"field_{field.id}": cell})
                    except Exception as exc:
                        errors[row.id] = self._message(exc)

                if values:
                    self._save(user, table, model, values)

                # The signal carries one message, so failed rows go per message.
                failed_by_message: dict[str, list] = {}
                for row in rows:
                    if row.id in errors:
                        failed_by_message.setdefault(errors[row.id], []).append(row)
                for message, failed in failed_by_message.items():
                    rows_ai_values_generation_error.send(
                        signal_sender or self,
                        user=user,
                        rows=failed,
                        field=field,
                        table=table,
                        error_message=message,
                    )
                if progress is not None:
                    progress.increment(by=len(chunk))
        return errors

    def transform_cells(
        self, job, field, progress: Optional[Progress] = None
    ) -> List[int]:
        """
        Rewrites the job's cells of a text field with its instruction. The answers
        are saved in one UpdateRowsActionType action, so the change can be undone
        and is in the row history. Empty cells are skipped.

        :return: The ids of the rows left unchanged: deleted, failed, or edited
            while the model ran.
        """

        table = field.table
        model = table.get_model()
        model_type = generative_ai_model_type_registry.get(job.ai_generative_ai_type)
        original = dict(
            model.objects.filter(id__in=job.row_ids).values_list("id", field.db_column)
        )
        failed = set(job.row_ids) - set(original)
        answers: dict[int, str] = {}
        to_send = {row_id: value for row_id, value in original.items() if value}
        if progress is not None:
            # Deleted and empty rows are done already.
            progress.increment(by=len(job.row_ids) - len(to_send))
        workers = max(1, settings.AI_TABLES_MAX_CONCURRENT_GENERATIONS)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    self._prompt_model,
                    model_type,
                    job.ai_generative_ai_model,
                    job.ai_temperature,
                    table.database.workspace,
                    TRANSFORM_PROMPT.format(instruction=job.instruction, text=value),
                    [],
                    None,
                ): row_id
                for row_id, value in to_send.items()
            }
            for future in as_completed(futures):
                row_id = futures[future]
                try:
                    answer = future.result()
                    text = "" if answer is None else str(answer).strip()
                    if not text:
                        # Saving it would wipe the cell.
                        raise RowGenerationError("The model returned no text.")
                    answers[row_id] = text[: settings.MAX_FIELD_TEXT_LENGTH]
                except Exception as exc:
                    self._message(exc)  # Logs unexpected errors.
                    failed.add(row_id)
                if progress is not None:
                    progress.increment()

        with transaction.atomic():
            # Locked, so a cell edited while the model ran is left as it was edited.
            current = dict(
                RowHandler()
                .get_rows_for_update(model, list(answers))
                .values_list("id", field.db_column)
            )
            rows_values = []
            for row_id, text in answers.items():
                if row_id not in current or current[row_id] != original[row_id]:
                    failed.add(row_id)
                elif text != original[row_id]:
                    rows_values.append({"id": row_id, f"field_{field.id}": text})
            if rows_values:
                action_type_registry.get_by_type(UpdateRowsActionType).do(
                    job.user, table, rows_values, model=model
                )
        return sorted(failed)

    def _message(self, exc: Exception) -> str:
        if isinstance(exc, (RowGenerationError, GenerativeAIPromptError)):
            return str(exc)
        logger.warning(f"AI prompt generation failed: {exc!r}")
        return get_user_friendly_error_message(exc)

    def run_auto_update(self, field_id: int, row_ids: List[int]):
        """
        Regenerates the rows of an auto-updating field as the user who turned the
        auto-update on. Skipped if that user can't update rows of the table anymore.
        """

        field = self.get_field(field_id)
        if field is None or field.trashed or not field.ai_auto_update:
            return
        user = field.ai_auto_update_user
        if user is None or not user.is_active:
            return
        table = field.table
        if not CoreHandler().check_permissions(
            user,
            UpdateDatabaseRowOperationType.type,
            workspace=table.database.workspace,
            context=table,
            raise_permission_exceptions=False,
        ):
            return
        self.generate_values(user, field, row_ids)
