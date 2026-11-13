from unittest.mock import patch

from django.db import connections
from django.test import override_settings
from django.urls import reverse

import pytest
from ai_tables.handler import AIPromptHandler
from ai_tables.models import AIPromptScheduledUpdate
from rest_framework.exceptions import ValidationError
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from baserow.contrib.database.fields.exceptions import (
    IncompatibleField,
    IncompatiblePrimaryFieldTypeError,
)
from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.rows.handler import RowHandler
from baserow.contrib.database.rows.models import RowHistory
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


def _transform(user, fields, row_ids):
    fields = fields if isinstance(fields, list) else [fields]
    return JobHandler().create_and_start_job(
        user,
        "transform_ai_cells",
        field_ids=[field.id for field in fields],
        row_ids=row_ids,
        instruction="Capitalize",
        ai_generative_ai_type="test_generative_ai",
        ai_generative_ai_model="test_1",
        sync=True,
    )


def _apply(job, cells=None):
    """Applies the job's proposals, all of them unless `cells` is given."""

    job.refresh_from_db()
    fields = [FieldHandler().get_field(field_id).specific for field_id in job.field_ids]
    if cells is None:
        cells = {(p["row_id"], p["field_id"]) for p in job.proposals}
    return AIPromptHandler().apply_cells(job.user, job, fields, cells)


@pytest.mark.django_db(transaction=True)
def test_transform_proposes_and_writes_only_what_is_applied(data_fixture):
    user, table, name = _setup(data_fixture)
    ada = RowHandler().create_row(user, table, {f"field_{name.id}": "ada"})
    bob = RowHandler().create_row(user, table, {f"field_{name.id}": "bob"})
    empty = RowHandler().create_row(user, table, {})

    job = _transform(user, name, [ada.id, bob.id, empty.id])

    job.refresh_from_db()
    assert job.state == "finished"
    assert job.failed_row_ids == []
    # Nothing is written until the user applies it.
    assert _cell(table, name, ada.id) == "ada"
    assert not RowHistory.objects.exists()
    # The fixture model echoes the prompt, which names the column and ends with
    # the cell's text. Empty cells get no proposal.
    by_row = {p["row_id"]: p for p in job.proposals}
    assert sorted(by_row) == [ada.id, bob.id]
    assert by_row[ada.id]["old"] == "ada"
    # Named by the primary field, as the grid shows the row.
    assert by_row[ada.id]["row_name"] == "ada"
    assert by_row[ada.id]["field_name"] == name.name
    assert f'column "{name.name}"' in by_row[ada.id]["new"]
    assert by_row[ada.id]["new"].endswith("Text:\nada")

    # Bob's change is rejected.
    written, skipped = _apply(job, {(ada.id, name.id)})

    assert (written, skipped) == (1, [])
    assert _cell(table, name, ada.id).endswith("Text:\nada")
    assert _cell(table, name, bob.id) == "bob"
    entry = RowHistory.objects.get(row_id=ada.id)
    assert entry.action_type == "update_rows"
    assert entry.before_values == {f"field_{name.id}": "ada"}


@pytest.mark.django_db(transaction=True)
def test_transform_never_blanks_or_overwrites_an_edited_cell(data_fixture):
    user, table, name = _setup(data_fixture)
    blank = RowHandler().create_row(user, table, {f"field_{name.id}": "ann"})
    edited = RowHandler().create_row(user, table, {f"field_{name.id}": "bob"})

    def answer(model_type, model, temperature, workspace, prompt, files, output):
        # Runs in a worker thread, like the real _prompt_model.
        try:
            return "  " if prompt.endswith("ann") else "BOB"
        finally:
            connections.close_all()

    with patch.object(AIPromptHandler, "_prompt_model", side_effect=answer):
        job = _transform(user, name, [blank.id, edited.id])
    job.refresh_from_db()
    assert job.failed_row_ids == [blank.id]
    # The user edits the cell before applying the proposal.
    RowHandler().update_rows(
        user, table, [{"id": edited.id, f"field_{name.id}": "Bobby"}]
    )

    written, skipped = _apply(job)

    assert (written, skipped) == (0, [edited.id])
    assert _cell(table, name, blank.id) == "ann"
    assert _cell(table, name, edited.id) == "Bobby"
    assert not RowHistory.objects.filter(row_id=blank.id).exists()


@pytest.mark.django_db
def test_transform_refuses_fields_that_are_not_writable_text(data_fixture):
    user, table, name = _setup(data_fixture)
    number = data_fixture.create_number_field(table=table)
    row = RowHandler().create_row(user, table, {})

    with pytest.raises(IncompatibleField):
        _transform(user, number, [row.id])

    name.read_only = True
    name.save()
    with pytest.raises(IncompatibleField):
        _transform(user, name, [row.id])

    other_table = data_fixture.create_database_table(database=table.database)
    other = data_fixture.create_text_field(table=other_table)
    name.read_only = False
    name.save()
    with pytest.raises(IncompatibleField):
        _transform(user, [name, other], [row.id])


@pytest.mark.django_db
def test_transform_refuses_more_cells_than_the_batch_limit(data_fixture):
    user, table, name = _setup(data_fixture)
    city = data_fixture.create_text_field(table=table, name="City")
    row = RowHandler().create_row(user, table, {})

    with override_settings(BATCH_ROWS_SIZE_LIMIT=1):
        with pytest.raises(ValidationError):
            _transform(user, [name, city], [row.id])


@pytest.mark.django_db(transaction=True)
def test_transform_several_columns_is_one_row_update(data_fixture):
    user, table, name = _setup(data_fixture)
    city = data_fixture.create_text_field(table=table, name="City")
    row = RowHandler().create_row(
        user, table, {f"field_{name.id}": "ada", f"field_{city.id}": "rome"}
    )

    job = _transform(user, [name, city], [row.id])
    written, skipped = _apply(job)

    job.refresh_from_db()
    assert job.state == "finished"
    assert job.failed_row_ids == []
    assert (written, skipped) == (2, [])
    assert _cell(table, name, row.id).endswith("Text:\nada")
    assert _cell(table, city, row.id).endswith("Text:\nrome")
    entry = RowHistory.objects.get(row_id=row.id)
    assert entry.before_values == {
        f"field_{name.id}": "ada",
        f"field_{city.id}": "rome",
    }


@pytest.mark.django_db(transaction=True)
def test_apply_endpoint_writes_accepted_cells_once_for_the_owner(
    api_client, data_fixture
):
    user, table, name = _setup(data_fixture)
    ada = RowHandler().create_row(user, table, {f"field_{name.id}": "ada"})
    bob = RowHandler().create_row(user, table, {f"field_{name.id}": "bob"})
    job = _transform(user, name, [ada.id, bob.id])
    url = reverse("api:ai_tables:apply_transform", kwargs={"job_id": job.id})
    body = {"cells": [{"row_id": ada.id, "field_id": name.id}]}

    other = data_fixture.create_user()
    response = api_client.post(
        url,
        body,
        format="json",
        HTTP_AUTHORIZATION=f"JWT {data_fixture.generate_token(other)}",
    )
    assert response.status_code == HTTP_404_NOT_FOUND
    assert _cell(table, name, ada.id) == "ada"

    token = data_fixture.generate_token(user)
    response = api_client.post(
        url, body, format="json", HTTP_AUTHORIZATION=f"JWT {token}"
    )
    assert response.status_code == HTTP_200_OK, response.json()
    assert response.json() == {"written": 1, "skipped_row_ids": []}
    assert _cell(table, name, ada.id).endswith("Text:\nada")
    # Not accepted, so rejected.
    assert _cell(table, name, bob.id) == "bob"

    response = api_client.post(
        url, body, format="json", HTTP_AUTHORIZATION=f"JWT {token}"
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_TRANSFORM_NOT_APPLICABLE"
