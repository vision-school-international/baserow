from django.urls import reverse

import pytest
from custom_code.models import MAX_CODE_LENGTH
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from baserow.contrib.builder.application_types import BuilderApplicationType
from baserow.core.registries import ImportExportConfig


def test_theme_serializers_include_the_custom_code():
    # They're built on first use; built while the builder app starts, they'd
    # miss this plugin's block (builder/api/theme/serializers.py `__getattr__`).
    from baserow.contrib.builder.api.theme.serializers import (
        CombinedThemeConfigBlocksRequestSerializer,
        CombinedThemeConfigBlocksSerializer,
    )

    for serializer_class in (
        CombinedThemeConfigBlocksRequestSerializer,
        CombinedThemeConfigBlocksSerializer,
    ):
        assert {"custom_css", "custom_js"} <= set(serializer_class().fields)


def _set_code(builder, css="", js=""):
    block = builder.customcodethemeconfigblock
    block.custom_css = css
    block.custom_js = js
    block.save()


@pytest.mark.django_db
def test_theme_update_sets_the_custom_code(api_client, data_fixture):
    # Like builder/api/theme/test_theme_views.py `test_update_theme`.
    user, token = data_fixture.create_user_and_token()
    builder = data_fixture.create_builder_application(user=user)
    url = reverse(
        "api:builder:builder_id:theme:update", kwargs={"builder_id": builder.id}
    )

    response = api_client.patch(
        url,
        {"custom_css": "h1 { color: red; }", "custom_js": "console.log(1)"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json()["custom_css"] == "h1 { color: red; }"
    assert response.json()["custom_js"] == "console.log(1)"

    too_long = api_client.patch(
        url,
        {"custom_css": "a" * (MAX_CODE_LENGTH + 1)},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert too_long.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.parametrize(
    "config_values,expected_untrusted",
    [
        ({}, True),
        ({"is_duplicate": True}, False),
        ({"is_publishing": True}, False),
        ({"is_template": True}, False),
    ],
)
def test_import_keeps_the_code_and_reports_it(
    data_fixture, config_values, expected_untrusted
):
    builder = data_fixture.create_builder_application()
    _set_code(builder, css="body { margin: 0; }", js="alert(1)")
    config = ImportExportConfig(include_permission_data=False, **config_values)
    application_type = BuilderApplicationType()

    serialized = application_type.export_serialized(builder, config)
    imported = application_type.import_serialized(
        builder.workspace, serialized, config, {}
    )
    imported.refresh_from_db()

    assert imported.customcodethemeconfigblock.custom_css == "body { margin: 0; }"
    assert imported.customcodethemeconfigblock.custom_js == "alert(1)"
    # From outside, the code stays off until the owner trusts it.
    assert imported.untrusted_content is expected_untrusted
    assert {"type": "custom_css"} in imported.import_report
    assert {"type": "custom_js"} in imported.import_report


@pytest.mark.django_db
def test_import_without_code_reports_nothing(data_fixture):
    builder = data_fixture.create_builder_application()
    config = ImportExportConfig(include_permission_data=False)
    application_type = BuilderApplicationType()

    serialized = application_type.export_serialized(builder, config)
    imported = application_type.import_serialized(
        builder.workspace, serialized, config, {}
    )
    imported.refresh_from_db()

    assert imported.untrusted_content is False
    assert imported.import_report == []


@pytest.mark.django_db
def test_theme_update_sets_and_validates_the_assets(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    builder = data_fixture.create_builder_application(user=user)
    url = reverse(
        "api:builder:builder_id:theme:update", kwargs={"builder_id": builder.id}
    )
    assets = [
        {"type": "stylesheet", "url": "https://a.test/a.css", "crossorigin": ""},
        {"type": "script", "url": "https://a.test/a.js", "load": "async"},
    ]

    response = api_client.patch(
        url, {"custom_assets": assets}, format="json", HTTP_AUTHORIZATION=f"JWT {token}"
    )

    assert response.status_code == HTTP_200_OK
    assert [a["url"] for a in response.json()["custom_assets"]] == [
        "https://a.test/a.css",
        "https://a.test/a.js",
    ]
    for bad in [
        {"type": "script", "url": "javascript:alert(1)"},
        {"type": "font", "url": "https://a.test/a.woff"},
        {"type": "script", "url": "https://a.test/a.js", "load": "later"},
    ]:
        response = api_client.patch(
            url,
            {"custom_assets": [bad]},
            format="json",
            HTTP_AUTHORIZATION=f"JWT {token}",
        )
        assert response.status_code == HTTP_400_BAD_REQUEST, bad


@pytest.mark.django_db
def test_import_reports_the_external_assets(data_fixture):
    builder = data_fixture.create_builder_application()
    block = builder.customcodethemeconfigblock
    block.custom_assets = [
        {"type": "stylesheet", "url": "https://a.test/a.css"},
        {"type": "script", "url": "https://a.test/a.js"},
    ]
    block.save()
    config = ImportExportConfig(include_permission_data=False)
    application_type = BuilderApplicationType()

    serialized = application_type.export_serialized(builder, config)
    imported = application_type.import_serialized(
        builder.workspace, serialized, config, {}
    )
    imported.refresh_from_db()

    assert imported.customcodethemeconfigblock.custom_assets == block.custom_assets
    assert imported.untrusted_content is True
    assert imported.import_report == [
        {"type": "external_stylesheet", "url": "https://a.test/a.css"},
        {"type": "external_script", "url": "https://a.test/a.js"},
    ]
