import io

from django.urls import reverse

import pytest
from PIL import Image
from telegram_share.share_cards import (
    _font,
    card_for_view,
    markdown_to_text,
    wrap,
)

from baserow.contrib.database.rows.handler import RowHandler


def _card_url(view):
    return reverse("api:telegram_share:share_card", kwargs={"slug": view.slug})


@pytest.mark.django_db
def test_form_card_shows_the_public_form(api_client, data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    name = data_fixture.create_text_field(table=table, name="Name")
    phone = data_fixture.create_text_field(table=table, name="Phone")
    data_fixture.create_text_field(table=table, name="Notes")
    form = data_fixture.create_form_view(
        table=table,
        public=True,
        title="Event sign-up",
        description="**Bring** a [friend](https://example.com).",
    )
    data_fixture.create_form_view_field_option(
        form, name, enabled=True, required=True, name="Your name", order=1
    )
    data_fixture.create_form_view_field_option(
        form, phone, enabled=True, required=False, order=2
    )

    card = card_for_view(form)

    assert card.kind == "form"
    assert card.title == "Event sign-up"
    assert card.description == "Bring a friend."
    # Only the enabled questions, with the form's own labels.
    assert card.items == [("Your name", True), ("Phone", False)]

    response = api_client.get(_card_url(form))
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert Image.open(io.BytesIO(response.content)).size == (1200, 630)


@pytest.mark.django_db
def test_untitled_form_card_never_shows_the_view_name(data_fixture):
    form = data_fixture.create_form_view(public=True, title="", name="Leads internal")

    assert card_for_view(form).title == "Form"


@pytest.mark.django_db
def test_view_card_leaves_out_hidden_fields(api_client, data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    primary = data_fixture.create_text_field(table=table, name="Route", primary=True)
    secret = data_fixture.create_text_field(table=table, name="Secret")
    grid = data_fixture.create_grid_view(table=table, public=True, name="Routes")
    data_fixture.create_grid_view_field_option(grid, primary, hidden=False)
    data_fixture.create_grid_view_field_option(grid, secret, hidden=True)
    for _ in range(2):
        RowHandler().create_row(user, table, {})

    card = card_for_view(grid)

    assert card.kind == "view"
    assert card.title == "Routes"
    assert card.items == [("Route", False)]
    assert card.description == "2 rows · 1 column"
    assert api_client.get(_card_url(grid)).status_code == 200


@pytest.mark.django_db
def test_no_card_for_private_or_password_views(api_client, data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    private = data_fixture.create_grid_view(table=table, public=False)
    protected = data_fixture.create_grid_view(table=table, public=True)
    protected.set_password("secret123")
    protected.save()

    assert api_client.get(_card_url(private)).status_code == 404
    assert api_client.get(_card_url(protected)).status_code == 404


def test_wrap_cuts_long_text_to_its_lines():
    font = _font(22, 400)

    lines = wrap("word " * 200, font, 400, 3)

    assert len(lines) == 3
    assert lines[-1].endswith("…")
    assert all(font.getlength(line) <= 400 for line in lines)
    # A word wider than the column is cut, not drawn past it.
    assert all(font.getlength(line) <= 100 for line in wrap("x" * 80, font, 100, 2))
    assert wrap("", font, 400, 3) == []


def test_markdown_to_text():
    assert markdown_to_text("# Hi\n\n- one\n- two  \nthree") == "Hi one two three"
    assert markdown_to_text(None) == ""
