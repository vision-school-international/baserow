from django.urls import reverse

import pytest
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from telegram_share.models import TelegramSendWorkflowAction

from baserow.contrib.database.fields.models import ButtonField
from baserow.contrib.database.table.handler import TableHandler


def _create(api_client, token, button, **values):
    return api_client.post(
        reverse("api:database:workflow_actions:list", kwargs={"field_id": button.id}),
        {"type": "telegram_send", **values},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )


@pytest.mark.django_db
def test_telegram_action_opens_a_new_tab_and_only_links_this_tables_forms(
    api_client, data_fixture
):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    other_table = data_fixture.create_database_table(user=user)
    button = data_fixture.create_button_field(table=table)
    form = data_fixture.create_form_view(table=table, public=True)
    other_form = data_fixture.create_form_view(table=other_table, public=True)

    response = _create(api_client, token, button, form_view_id=other_form.id)
    assert response.status_code == HTTP_400_BAD_REQUEST

    response = _create(
        api_client,
        token,
        button,
        recipient={"formula": "'@ada'", "mode": "simple"},
        form_view_id=form.id,
        prefill=True,
    )
    assert response.status_code == HTTP_200_OK, response.json()
    assert response.json()["form_view_id"] == form.id
    assert response.json()["form"]["slug"] == str(form.slug)
    action = TelegramSendWorkflowAction.objects.get()
    # Forced, so the button opens its tab on click like an open URL action.
    assert action.target == "blank"
    assert ButtonField.objects.get(id=button.id).opens_new_tab is True


@pytest.mark.django_db
def test_dispatch_hands_the_browser_the_form_link_details(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    name = data_fixture.create_text_field(table=table, name="Name")
    hidden = data_fixture.create_text_field(table=table, name="Hidden")
    button = data_fixture.create_button_field(table=table)
    form = data_fixture.create_form_view(table=table, public=True)
    data_fixture.create_form_view_field_option(form, name, enabled=True)
    data_fixture.create_form_view_field_option(form, hidden, enabled=False)
    data_fixture.create_database_workflow_action(
        TelegramSendWorkflowAction,
        field=button,
        recipient={"formula": "'ada'", "mode": "simple"},
        form_view=form,
        prefill=True,
        target="blank",
    )
    row = table.get_model().objects.create()

    response = api_client.post(
        reverse(
            "api:database:workflow_actions:dispatch", kwargs={"field_id": button.id}
        ),
        {"row_id": row.id},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_200_OK, response.json()
    (client_action,) = response.json()["client_actions"]
    assert client_action["type"] == "telegram_send"
    assert client_action["recipient"]["formula"] == "'ada'"
    assert client_action["prefill"] is True
    assert client_action["form"] == {
        "slug": str(form.slug),
        "public": True,
        "field_ids": [name.id],
    }


@pytest.mark.django_db
def test_a_trashed_form_is_hidden_but_the_action_still_saves(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    button = data_fixture.create_button_field(table=table)
    form = data_fixture.create_form_view(table=table, public=True)
    action = data_fixture.create_database_workflow_action(
        TelegramSendWorkflowAction, field=button, form_view=form, target="blank"
    )
    form.trashed = True
    form.save()

    response = api_client.patch(
        reverse(
            "api:database:workflow_actions:item",
            kwargs={"workflow_action_id": action.id},
        ),
        {"message": {"formula": "'hi'", "mode": "simple"}, "form_view_id": form.id},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_200_OK, response.json()
    assert response.json()["form"] is None
    action.refresh_from_db()
    assert action.form_view_id == form.id


@pytest.mark.django_db
def test_duplicating_the_table_links_the_copy_of_the_form(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    button = data_fixture.create_button_field(table=table, name="btn")
    form = data_fixture.create_form_view(table=table, public=True, name="Sign up")
    data_fixture.create_database_workflow_action(
        TelegramSendWorkflowAction, field=button, form_view=form, target="blank"
    )

    duplicated = TableHandler().duplicate_table(user, table)
    duplicated_button = duplicated.field_set.get(name="btn")
    action = TelegramSendWorkflowAction.objects.get(field=duplicated_button)

    assert action.form_view.table_id == duplicated.id
    assert action.form_view.name == "Sign up"
    assert action.target == "blank"
