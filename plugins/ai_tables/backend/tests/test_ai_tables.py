from unittest.mock import patch

import pytest
from ai_tables.handler import AIPromptHandler
from ai_tables.models import AIPromptScheduledUpdate

from baserow.contrib.database.fields.exceptions import (
    IncompatiblePrimaryFieldTypeError,
)
from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.rows.handler import RowHandler
from baserow.core.generative_ai.exceptions import ModelDoesNotBelongToType
from baserow.core.jobs.handler import JobHandler


def _setup(data_fixture):
    data_fixture.register_fake_generate_ai_type()
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    name = data_fixture.create_text_field(table=table, name="Name", primary=True)
    return user, table, name


def _create_ai_field(user, table, name, type_name="ai_prompt_text", **kwargs):
    values = {
        "name": "AI",
        "ai_generative_ai_type": "test_generative_ai",
        "ai_generative_ai_model": "test_1",
        "ai_prompt": {
            "formula": f"concat('Hi ', get('fields.field_{name.id}'))",
            "mode": "advanced",
        },
        **kwargs,
    }
    return FieldHandler().create_field(user, table, type_name, **values)


def _cell(table, field, row_id):
    row = table.get_model().objects.get(id=row_id)
    return getattr(row, f"field_{field.id}")


@pytest.mark.django_db
def test_generates_text_from_the_row(data_fixture):
    user, table, name = _setup(data_fixture)
    field = _create_ai_field(user, table, name)
    row = RowHandler().create_row(user, table, {f"field_{name.id}": "Ada"})

    errors = AIPromptHandler().generate_values(user, field, [row.id])

    assert errors == {}
    assert _cell(table, field, row.id) == "Generated with temperature None: Hi Ada"


@pytest.mark.django_db
def test_choice_field_stores_the_picked_option(data_fixture):
    user, table, name = _setup(data_fixture)
    field = _create_ai_field(
        user,
        table,
        name,
        type_name="ai_prompt_choice",
        select_options=[
            {"value": "Yes", "color": "green"},
            {"value": "No", "color": "red"},
        ],
    )
    row = RowHandler().create_row(user, table, {f"field_{name.id}": "Ada"})

    AIPromptHandler().generate_values(user, field, [row.id])

    # The fixture model answers the first option it is offered.
    assert _cell(table, field, row.id).value == "Yes"


@pytest.mark.django_db
def test_model_must_be_enabled_for_ai_fields(data_fixture):
    user, table, name = _setup(data_fixture)

    with pytest.raises(ModelDoesNotBelongToType):
        _create_ai_field(user, table, name, ai_generative_ai_model="missing")


@pytest.mark.django_db
def test_ai_field_can_not_be_primary(data_fixture):
    user, table, name = _setup(data_fixture)

    with pytest.raises(IncompatiblePrimaryFieldTypeError):
        FieldHandler().update_field(
            user,
            name,
            new_type_name="ai_prompt_text",
            ai_generative_ai_type="test_generative_ai",
            ai_generative_ai_model="test_1",
        )


@pytest.mark.django_db
def test_failed_rows_are_reported_and_left_unchanged(data_fixture):
    user, table, name = _setup(data_fixture)
    field = _create_ai_field(user, table, name)
    row = RowHandler().create_row(user, table, {f"field_{name.id}": "Ada"})
    field.ai_generative_ai_type = "test_generative_ai_prompt_error"
    field.save()

    with patch("ai_tables.handler.rows_ai_values_generation_error.send") as send_error:
        errors = AIPromptHandler().generate_values(user, field, [row.id])

    assert errors == {row.id: "Test error"}
    assert _cell(table, field, row.id) in (None, "")
    send_error.assert_called_once()
    assert send_error.call_args.kwargs["error_message"] == "Test error"


@pytest.mark.django_db(transaction=True)
def test_job_only_fills_empty_cells(data_fixture):
    user, table, name = _setup(data_fixture)
    field = _create_ai_field(user, table, name)
    filled = RowHandler().create_row(
        user, table, {f"field_{name.id}": "Ada", f"field_{field.id}": "Keep"}
    )
    empty = RowHandler().create_row(user, table, {f"field_{name.id}": "Bob"})

    job = JobHandler().create_and_start_job(
        user,
        "generate_ai_prompt_values",
        field_id=field.id,
        only_empty=True,
        sync=True,
    )

    job.refresh_from_db()
    assert job.state == "finished"
    assert _cell(table, field, filled.id) == "Keep"
    assert _cell(table, field, empty.id).endswith("Hi Bob")


@pytest.mark.django_db
def test_changing_a_prompt_field_schedules_the_row(data_fixture):
    user, table, name = _setup(data_fixture)
    field = _create_ai_field(user, table, name, ai_auto_update=True)
    row = RowHandler().create_row(user, table, {f"field_{name.id}": "Ada"})
    AIPromptScheduledUpdate.objects.all().delete()

    RowHandler().update_row_by_id(user, table, row.id, {f"field_{name.id}": "Bob"})

    scheduled = AIPromptScheduledUpdate.objects.values_list("field_id", "row_id")
    assert list(scheduled) == [(field.id, row.id)]
    field.refresh_from_db()
    assert field.ai_auto_update_user_id == user.id
