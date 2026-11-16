from django.core.exceptions import ValidationError
from django.shortcuts import reverse

import pytest
from pydantic import ValidationError as PydanticValidationError
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.rows.handler import RowHandler
from baserow.contrib.database.tools.fields import (
    FieldItemCreate,
    FieldItemUpdate,
    create_fields,
    update_fields,
)
from baserow.core.tools import ToolContext


def _code_field(user, table, name="Code", **kwargs):
    return FieldHandler().create_field(
        user,
        table,
        "pattern_text",
        name=name,
        pattern=r"[A-Z]{3}-\d{3}",
        pattern_case="upper",
        pattern_error_message="Use ABC-123",
        **kwargs,
    )


def _phone_field(user, table, name="Phone", country="US"):
    return FieldHandler().create_field(
        user,
        table,
        "international_phone",
        name=name,
        phone_default_country=country,
    )


@pytest.mark.django_db
def test_international_phone_stores_the_international_format(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = _phone_field(user, table)
    anywhere = _phone_field(user, table, name="Anywhere", country="")
    name, anywhere_name = f"field_{field.id}", f"field_{anywhere.id}"

    row = RowHandler().create_row(
        user,
        table,
        {name: " (415) 555-2671 ", anywhere_name: "+44 20 7946 0958"},
    )
    assert getattr(row, name) == "+1 415-555-2671"
    assert getattr(row, anywhere_name) == "+44 20 7946 0958"
    # Another country's number, typed with its code.
    row = RowHandler().create_row(user, table, {name: "+61 2 9374 4000"})
    assert getattr(row, name) == "+61 2 9374 4000"
    empty = RowHandler().create_row(user, table, {name: ""})
    assert getattr(empty, name) in ("", None)

    with pytest.raises(ValidationError, match="valid phone number"):
        RowHandler().create_row(user, table, {name: "12345"})
    with pytest.raises(ValidationError, match="Start the number with \\+"):
        RowHandler().create_row(user, table, {anywhere_name: "4155552671"})


@pytest.mark.django_db
def test_telegram_username_stores_at_name(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user, table, "telegram_username", name="Telegram"
    )
    name = f"field_{field.id}"

    for typed in ["jane_doe", " @jane_doe ", "https://t.me/jane_doe", "t.me/jane_doe"]:
        row = RowHandler().create_row(user, table, {name: typed})
        assert getattr(row, name) == "@jane_doe"
    # 2 to 32 characters (owner's rule).
    assert getattr(RowHandler().create_row(user, table, {name: "ab"}), name) == "@ab"
    empty = RowHandler().create_row(user, table, {name: ""})
    assert getattr(empty, name) in ("", None)

    for bad in [
        "a",
        "a" * 33,
        "jane-doe",
        "jane doe",
        "@",
        "+15555550100",
        "15555550100",
    ]:
        with pytest.raises(ValidationError, match="Enter a Telegram username"):
            RowHandler().create_row(user, table, {name: bad})


@pytest.mark.django_db
def test_time_of_day_stores_24_hour_hh_mm(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user, table, "time_of_day", name="Start", time_format="12"
    )
    assert field.time_format == "12"
    name = f"field_{field.id}"

    for typed, stored in [
        ("14:30", "14:30"),
        ("9:05", "09:05"),
        (" 2:30 pm ", "14:30"),
        ("2PM", "14:00"),
        ("12:00 a.m.", "00:00"),
        ("12 pm", "12:00"),
        ("14:30:00", "14:30"),
    ]:
        row = RowHandler().create_row(user, table, {name: typed})
        assert getattr(row, name) == stored, typed
    empty = RowHandler().create_row(user, table, {name: ""})
    assert getattr(empty, name) in ("", None)

    for bad in ["14", "24:00", "12:60", "13 pm", "9:5", "14:30:15", "noon"]:
        with pytest.raises(ValidationError):
            RowHandler().create_row(user, table, {name: bad})

    with pytest.raises(ValidationError, match="isn't 24 or 12"):
        FieldHandler().update_field(user, field, time_format="6")


@pytest.mark.django_db
def test_converted_text_field_drops_its_default(data_fixture):
    # A text default survives the conversion (shared TextField column); new rows
    # must not get it, or the check refuses every row created without the field.
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = data_fixture.create_text_field(table=table, text_default="TBD")
    FieldHandler().update_field(user, field, new_type_name="telegram_username")

    row = RowHandler().create_row(user, table, {})

    assert getattr(row, f"field_{field.id}") in ("", None)


@pytest.mark.django_db
def test_converting_a_text_field_cleans_its_values(data_fixture):
    # The SQL in telegram.py / times.py CONVERT_SQL must agree with the cleaners.
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    cases = {
        "telegram_username": [
            (" @jane_doe ", "@jane_doe"),
            ("https://t.me/Jane_Doe", "@Jane_Doe"),
            ("jane_doe", "@jane_doe"),
            ("15555550100", ""),
            ("+15555550100", ""),
            ("ab", "@ab"),
            ("a", ""),
            ("jane doe", ""),
            ("", ""),
            (None, None),
        ],
        "time_of_day": [
            ("14:30", "14:30"),
            (" 2:30 pm ", "14:30"),
            ("12:00 a.m.", "00:00"),
            ("14:30:00", "14:30"),
            ("14", ""),
            ("13 pm", ""),
            ("24:00", ""),
            ("noon", ""),
            (None, None),
        ],
    }
    for type_name, values in cases.items():
        field = data_fixture.create_text_field(table=table, name=type_name)
        name = f"field_{field.id}"
        rows = [
            RowHandler().create_row(user, table, {name: typed}) for typed, _ in values
        ]

        FieldHandler().update_field(user, field, new_type_name=type_name)

        model = table.get_model()
        for row, (typed, stored) in zip(rows, values):
            assert getattr(model.objects.get(id=row.id), name) == stored, typed


@pytest.mark.django_db
def test_agent_field_tools_create_telegram_username(table_ctx):
    ctx, table = table_ctx

    result = create_fields(
        ctx, table.id, [FieldItemCreate(name="Telegram", type="telegram")]
    )

    (created,) = result["created_fields"]
    assert created["type"] == "telegram_username"


@pytest.mark.django_db
def test_agent_field_tools_create_and_update_time_of_day(table_ctx):
    ctx, table = table_ctx

    result = create_fields(
        ctx, table.id, [FieldItemCreate(name="Start", type="time", time_format="12")]
    )

    (created,) = result["created_fields"]
    assert created["type"] == "time_of_day"
    assert created["time_format"] == "12"

    field = table.field_set.get(name="Start")
    result = update_fields(ctx, [FieldItemUpdate(field_id=field.id, time_format="24")])
    assert result["updated_fields"][0]["time_format"] == "24"


@pytest.mark.django_db
def test_international_phone_refuses_unknown_countries(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)

    with pytest.raises(ValidationError, match="isn't a supported country"):
        _phone_field(user, table, country="XX")


@pytest.mark.django_db
def test_pattern_text_cleans_then_checks_values(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = _code_field(user, table)
    name = f"field_{field.id}"

    row = RowHandler().create_row(user, table, {name: "  abc-123 "})
    assert getattr(row, name) == "ABC-123"
    empty = RowHandler().create_row(user, table, {name: ""})
    assert getattr(empty, name) in ("", None)

    with pytest.raises(ValidationError, match="Use ABC-123"):
        RowHandler().create_row(user, table, {name: "abc"})


@pytest.mark.django_db
def test_pattern_text_stops_slow_patterns(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user, table, "pattern_text", name="Slow", pattern=r"(a|aa)+"
    )

    with pytest.raises(ValidationError, match="too long"):
        RowHandler().create_row(user, table, {f"field_{field.id}": "a" * 60 + "b"})


@pytest.mark.django_db
def test_pattern_text_api_refuses_bad_patterns_and_values(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)

    response = api_client.post(
        reverse("api:database:fields:list", kwargs={"table_id": table.id}),
        {"name": "Bad", "type": "pattern_text", "pattern": "("},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == HTTP_400_BAD_REQUEST

    field = _code_field(user, table)
    url = reverse("api:database:rows:list", kwargs={"table_id": table.id})
    response = api_client.post(
        url,
        {f"field_{field.id}": "abc"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response.json()["detail"] == "Use ABC-123"

    response = api_client.post(
        url,
        {f"field_{field.id}": " xyz-789"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == HTTP_200_OK
    assert response.json()[f"field_{field.id}"] == "XYZ-789"

    # Without trim, the API keeps the spaces, so the value doesn't match.
    untrimmed = _code_field(user, table, name="Untrimmed", pattern_trim=False)
    response = api_client.post(
        url,
        {f"field_{untrimmed.id}": " XYZ-789"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_public_form_checks_a_value_before_submitting(api_client, data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = _code_field(user, table)
    hidden = _code_field(user, table, name="Hidden")
    phone = _phone_field(user, table)
    plain = data_fixture.create_text_field(table=table, name="Plain")
    form = data_fixture.create_form_view(table=table, public=True)
    data_fixture.create_form_view_field_option(form, field, enabled=True)
    data_fixture.create_form_view_field_option(form, hidden, enabled=False)
    data_fixture.create_form_view_field_option(form, phone, enabled=True)
    data_fixture.create_form_view_field_option(form, plain, enabled=True)

    def check(field_id, value):
        return api_client.post(
            reverse(
                "api:database:fields:field_patterns:check_form_value",
                kwargs={"slug": form.slug, "field_id": field_id},
            ),
            {"value": value},
            format="json",
        )

    response = check(field.id, " abc-123")
    assert response.status_code == HTTP_200_OK
    assert response.json() == {"valid": True, "error": None}

    response = check(field.id, "abc")
    assert response.json() == {"valid": False, "error": "Use ABC-123"}

    assert check(phone.id, "(415) 555-2671").json()["valid"] is True
    assert check(phone.id, "12345").json() == {
        "valid": False,
        "error": "Enter a valid phone number.",
    }

    assert check(hidden.id, "abc").status_code == HTTP_404_NOT_FOUND
    # Only the plugin's fields are checked.
    assert check(plain.id, "abc").status_code == HTTP_404_NOT_FOUND
    # Nothing is saved.
    assert table.get_model().objects.count() == 0


@pytest.fixture
def table_ctx(data_fixture):
    # Like database/tools/test_field_tools.py `table_ctx`.
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    data_fixture.create_text_field(table=table, name="Name", primary=True)
    return ToolContext(user=user, workspace=workspace), table


@pytest.mark.django_db
def test_agent_field_tools_create_and_update_pattern_text(table_ctx):
    ctx, table = table_ctx

    result = create_fields(
        ctx,
        table.id,
        [
            FieldItemCreate(
                name="Telegram",
                type="pattern_text",
                pattern=r"@[A-Za-z0-9_]{5,32}",
                pattern_error_message="Use @name",
                pattern_case="lower",
            )
        ],
    )

    (created,) = result["created_fields"]
    assert created["type"] == "pattern_text"
    assert created["pattern"] == r"@[A-Za-z0-9_]{5,32}"
    assert created["pattern_case"] == "lower"
    field = table.field_set.get(name="Telegram").specific
    with pytest.raises(ValidationError, match="Use @name"):
        RowHandler().create_row(ctx.user, table, {f"field_{field.id}": "nope"})

    result = update_fields(
        ctx, [FieldItemUpdate(field_id=field.id, pattern=r"@\w{5,32}")]
    )
    assert result["updated_fields"][0]["pattern"] == r"@\w{5,32}"


@pytest.mark.django_db
def test_agent_field_tools_refuse_bad_patterns(table_ctx):
    ctx, table = table_ctx

    with pytest.raises(PydanticValidationError, match="pattern_text requires"):
        FieldItemCreate(name="No pattern", type="pattern_text")

    result = create_fields(
        ctx, table.id, [FieldItemCreate(name="Bad", type="pattern_text", pattern="(")]
    )

    assert result["created_fields"] == []
    (error,) = result["errors"]
    assert error["code"] == "invalid_input"
    assert "valid regular expression" in error["message"]
    assert not table.field_set.filter(name="Bad").exists()


@pytest.mark.django_db
def test_agent_field_tools_create_and_update_international_phone(table_ctx):
    ctx, table = table_ctx

    result = create_fields(
        ctx,
        table.id,
        [
            FieldItemCreate(
                name="Phone", type="international_phone", phone_default_country="GB"
            ),
            FieldItemCreate(
                name="Bad", type="international_phone", phone_default_country="XX"
            ),
        ],
    )

    (created,) = result["created_fields"]
    assert created["type"] == "international_phone"
    assert created["phone_default_country"] == "GB"
    (error,) = result["errors"]
    assert "isn't a supported country" in error["message"]

    field = table.field_set.get(name="Phone")
    result = update_fields(
        ctx, [FieldItemUpdate(field_id=field.id, phone_default_country="")]
    )
    assert result["updated_fields"][0]["phone_default_country"] == ""
