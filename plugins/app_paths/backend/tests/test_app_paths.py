from django.test import override_settings
from django.urls import reverse

import pytest
from app_paths.models import PathDomain
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from baserow.contrib.builder.domains.handler import DomainHandler

HOST = "apps.example.com"


def _create(api_client, token, builder, domain_name):
    # Like builder/api/domains/test_domain_views.py `test_create_domain`.
    return api_client.post(
        reverse(
            "api:builder:builder_id:domains:list", kwargs={"builder_id": builder.id}
        ),
        {"type": "path", "domain_name": domain_name},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )


@pytest.mark.django_db
@override_settings(BASEROW_APP_PATHS_HOST=HOST)
def test_create_path_domain(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    builder = data_fixture.create_builder_application(user=user)

    response = _create(api_client, token, builder, f"ygmc.{HOST}")

    assert response.status_code == HTTP_200_OK, response.json()
    assert response.json()["type"] == "path"
    for bad in [
        f"YGMC.{HOST}",
        f"a.b.{HOST}",
        f"ygmc\n.{HOST}",
        "ygmc.other.com",
        HOST,
    ]:
        response = _create(api_client, token, builder, bad)
        assert response.status_code == HTTP_400_BAD_REQUEST, bad


@pytest.mark.django_db
@override_settings(BASEROW_APP_PATHS_HOST="")
def test_path_domains_are_off_without_a_host(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    builder = data_fixture.create_builder_application(user=user)

    assert _create(api_client, token, builder, f"ygmc.{HOST}").status_code == (
        HTTP_400_BAD_REQUEST
    )


@pytest.mark.django_db
@override_settings(
    BASEROW_APP_PATHS_HOST=HOST, PUBLIC_WEB_FRONTEND_URL="https://baserow.test"
)
def test_published_path_domain_is_found_by_its_name(data_fixture):
    builder = data_fixture.create_builder_application()
    domain = PathDomain.objects.create(
        builder=builder, domain_name=f"ygmc.{HOST}", order=1
    )

    assert domain.get_public_url() == f"https://{HOST}/ygmc"
    published = DomainHandler().publish(domain).published_to
    found = DomainHandler().get_public_builder_by_domain_name(f"ygmc.{HOST}")
    assert found.id == published.id
