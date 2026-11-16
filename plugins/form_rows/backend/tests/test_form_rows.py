from django.urls import reverse

import pytest
from form_rows.models import FormRowsSettings
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)

from baserow.contrib.database.fields.models import FormViewEditRowField
from baserow.contrib.database.rows.handler import RowHandler
from baserow.contrib.database.views.models import GridViewFieldOptions


def _settings_url(form):
    return reverse("api:form_rows:settings", kwargs={"view_id": form.id})


def _public_url(form):
    return reverse("api:form_rows:public", kwargs={"slug": form.slug})


@pytest.fixture
def routes(data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    other = data_fixture.create_database_table(database=table.database)
    driver = data_fixture.create_text_field(table=table, name="Driver", primary=True)
    secret = data_fixture.create_text_field(table=table, name="Secret")
    passengers = data_fixture.create_link_row_field(
        table=table, name="Passengers", link_row_table=other
    )
    grid = data_fixture.create_grid_view(table=table, name="Grid")
    data_fixture.create_grid_view_field_option(grid, driver, hidden=False)
    data_fixture.create_grid_view_field_option(grid, secret, hidden=True)
    data_fixture.create_grid_view_field_option(grid, passengers, hidden=False)
    form = data_fixture.create_form_view(
        table=table, public=True, mode="form_with_rows"
    )
    linked = RowHandler().create_row(user, other, {})
    first = RowHandler().create_row(
        user,
        table,
        {
            f"field_{driver.id}": "Ruth Kim",
            f"field_{secret.id}": "s3cret-value-xq",
            f"field_{passengers.id}": [linked.id],
        },
    )
    RowHandler().create_row(user, table, {})  # empty: left out of the list
    return {
        "user": user,
        "token": token,
        "table": table,
        "other": other,
        "grid": grid,
        "form": form,
        "driver": driver,
        "passengers": passengers,
        "first": first,
    }


@pytest.mark.django_db
def test_public_list_shows_the_views_public_cells(api_client, routes):
    form, grid = routes["form"], routes["grid"]
    FormRowsSettings.objects.create(
        form_view=form, list_view=grid, heading="Existing routes"
    )

    response = api_client.get(_public_url(form))

    assert response.status_code == HTTP_200_OK
    data = response.json()
    assert data["heading"] == "Existing routes"
    assert [f["name"] for f in data["fields"]] == ["Driver", "Passengers"]
    assert len(data["rows"]) == 1
    values = data["rows"][0]["values"]
    assert values[f"field_{routes['driver'].id}"] == "Ruth Kim"
    # A count, never the linked rows' names; hidden fields never sent.
    assert values[f"field_{routes['passengers'].id}"] == 1
    assert "s3cret-value-xq" not in str(data)
    assert data["rows"][0]["edit_url"] is None


@pytest.mark.django_db
def test_public_list_only_for_forms_in_the_mode(api_client, data_fixture, routes):
    form = routes["form"]
    form.mode = "form"
    form.save()
    assert api_client.get(_public_url(form)).status_code == HTTP_404_NOT_FOUND

    protected = data_fixture.create_form_view(
        table=routes["table"], public=True, mode="form_with_rows"
    )
    protected.set_password("secret123")
    protected.save()
    response = api_client.get(_public_url(protected))
    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_settings_refuse_views_of_other_tables_and_forms(
    api_client, data_fixture, routes
):
    form, token = routes["form"], routes["token"]
    elsewhere = data_fixture.create_grid_view(table=routes["other"])

    for view in (elsewhere, form):
        response = api_client.patch(
            _settings_url(form),
            {"list_view_id": view.id},
            format="json",
            HTTP_AUTHORIZATION=f"JWT {token}",
        )
        assert response.status_code == HTTP_400_BAD_REQUEST
        assert response.json()["error"] == "ERROR_FORM_ROWS_INVALID_VIEW"


@pytest.mark.django_db
def test_allowing_edit_adds_a_hidden_edit_link_field(api_client, routes):
    form, grid, token = routes["form"], routes["grid"], routes["token"]

    response = api_client.patch(
        _settings_url(form),
        {"list_view_id": grid.id, "allow_edit": True, "heading": "Existing routes"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_200_OK
    field = FormViewEditRowField.objects.get(table=routes["table"])
    assert field.name == "Edit link"
    assert field.form_view_id == form.id
    assert response.json()["edit_field_id"] == field.id
    # Hidden in the grid, so a public grid share doesn't hand out the links.
    assert GridViewFieldOptions.objects.get(grid_view=grid, field=field).hidden
    edit_url = response.json()["list"]["rows"][0]["edit_url"]
    assert f"form/{form.slug}/?edit_token=" in edit_url

    # Turning it on again reuses the field.
    api_client.patch(
        _settings_url(form),
        {"allow_edit": True},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert FormViewEditRowField.objects.filter(table=routes["table"]).count() == 1


@pytest.mark.django_db
def test_settings_need_access_to_the_form(api_client, data_fixture, routes):
    _, other_token = data_fixture.create_user_and_token()

    response = api_client.get(
        _settings_url(routes["form"]), HTTP_AUTHORIZATION=f"JWT {other_token}"
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_USER_NOT_IN_GROUP"
