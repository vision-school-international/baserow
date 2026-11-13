from django.core.exceptions import ValidationError
from django.shortcuts import reverse

import pytest
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.rows.handler import RowHandler


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
