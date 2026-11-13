import time
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

import jwt
import pytest
import responses
from cryptography.hazmat.primitives.asymmetric import rsa
from intercp_auth import oidc
from intercp_auth.models import InterCPAuthProviderModel
from intercp_auth.sync import add_to_default_workspace, enforce_single_sign_on

from baserow.core.auth_provider.handler import PasswordProviderHandler
from baserow.core.cache import global_cache
from baserow.core.handler import CoreHandler
from baserow.core.registries import auth_provider_type_registry

ISSUER = "https://auth.example.test/application/o/baserow/"
CLIENT_ID = "baserow-client"
CLIENT_SECRET = "baserow-secret"
AUTHORIZE = "https://auth.example.test/application/o/authorize/"
TOKEN = "https://auth.example.test/application/o/token/"
USERINFO = "https://auth.example.test/application/o/userinfo/"
JWKS = ISSUER + "jwks/"
KID = "key-1"
FRONTEND = "https://baserow.example.test"
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def intercp(settings):
    settings.INTERCP_OIDC_ISSUER = ISSUER
    settings.INTERCP_OIDC_CLIENT_ID = CLIENT_ID
    settings.INTERCP_OIDC_CLIENT_SECRET = CLIENT_SECRET
    settings.INTERCP_OIDC_NAME = "InterCP"
    settings.PUBLIC_BACKEND_URL = FRONTEND
    settings.PUBLIC_WEB_FRONTEND_URL = FRONTEND
    oidc._wellknown.cache_clear()
    global_cache.invalidate(f"intercp_auth_jwks_{JWKS}")
    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        http.get(
            ISSUER + ".well-known/openid-configuration",
            json={
                "issuer": ISSUER,
                "authorization_endpoint": AUTHORIZE,
                "token_endpoint": TOKEN,
                "userinfo_endpoint": USERINFO,
                "jwks_uri": JWKS,
            },
        )
        http.get(
            JWKS,
            json={
                "keys": [
                    {
                        **jwt.algorithms.RSAAlgorithm.to_jwk(
                            SIGNING_KEY.public_key(), as_dict=True
                        ),
                        "kid": KID,
                    }
                ]
            },
        )
        yield http
    oidc._wellknown.cache_clear()
    global_cache.invalidate(f"intercp_auth_jwks_{JWKS}")


def id_token(**overrides):
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "sub": "user-1",
        "iat": now,
        "exp": now + 300,
        "email": "nerdy_koala@visionschool.dev",
        "email_verified": True,
        "name": "Anthony",
        **overrides,
    }
    return jwt.encode(claims, SIGNING_KEY, algorithm="RS256", headers={"kid": KID})


def start_flow(api_client, query=""):
    response = api_client.get(reverse("api:intercp_auth:login") + query)
    assert response.status_code == 302
    return parse_qs(urlsplit(response["Location"]).query)


def finish_flow(api_client, http, params, **token_claims):
    http.post(
        TOKEN,
        json={
            "access_token": "access",
            "token_type": "Bearer",
            "id_token": id_token(**token_claims),
        },
    )
    return api_client.get(
        reverse("api:intercp_auth:callback"),
        {"state": params["state"][0], "code": "the-code"},
    )


def error_of(response):
    assert response.status_code == 302
    url = urlsplit(response["Location"])
    assert url.path == "/login/intercp-error"
    return parse_qs(url.query)["error"][0]


@pytest.mark.django_db
def test_enforce_single_sign_on(intercp, data_fixture):
    data_fixture.create_password_provider(enabled=True)
    user = data_fixture.create_user(password="a-password", is_staff=True)

    enforce_single_sign_on()
    enforce_single_sign_on()  # Idempotent.

    assert InterCPAuthProviderModel.objects.filter(enabled=True).count() == 1
    assert PasswordProviderHandler.get().enabled is False
    user.refresh_from_db()
    assert user.password == ""
    assert CoreHandler().get_settings().show_admin_signup_page is False


@pytest.mark.django_db
def test_enforce_single_sign_on_refuses_without_configuration(settings, data_fixture):
    settings.INTERCP_OIDC_ISSUER = ""
    data_fixture.create_password_provider(enabled=True)

    with pytest.raises(ImproperlyConfigured):
        enforce_single_sign_on()

    assert PasswordProviderHandler.get().enabled is True
    assert not InterCPAuthProviderModel.objects.exists()


@pytest.mark.django_db
def test_login_options_offer_only_intercp(intercp, data_fixture):
    data_fixture.create_password_provider(enabled=True)
    enforce_single_sign_on()

    options = auth_provider_type_registry.get_all_available_login_options()

    assert list(options) == ["intercp"]
    assert options["intercp"]["items"][0]["redirect_url"] == (
        FRONTEND + reverse("api:intercp_auth:login")
    )
    # Without it the login page waits for the user to press the button.
    assert "default_redirect_url" not in options["intercp"]


@pytest.mark.django_db
def test_login_redirects_with_state(intercp, api_client):
    params = start_flow(api_client)

    assert params["response_type"] == ["code"]
    assert params["client_id"] == [CLIENT_ID]
    callback = FRONTEND + reverse("api:intercp_auth:callback")
    assert params["redirect_uri"] == [callback]
    assert params["scope"] == ["openid email profile"]
    assert params["state"]


@pytest.mark.django_db
def test_callback_creates_user_and_signs_in(intercp, api_client, data_fixture):
    data_fixture.create_password_provider(enabled=True)
    enforce_single_sign_on()
    params = start_flow(api_client, "?original=/workspace/1")

    response = finish_flow(api_client, intercp, params)

    assert response.status_code == 302
    url = urlsplit(response["Location"])
    assert f"{url.scheme}://{url.netloc}{url.path}" == FRONTEND + "/workspace/1"
    query = parse_qs(url.query)
    assert query["token"] and query["user_session"]
    user = get_user_model().objects.get(email="nerdy_koala@visionschool.dev")
    assert user.password == ""
    assert user.profile.email_verified is True


@pytest.mark.django_db
def test_callback_adds_user_to_default_workspace(
    intercp, settings, api_client, data_fixture
):
    workspace = data_fixture.create_workspace()
    settings.INTERCP_DEFAULT_WORKSPACE_ID = workspace.id
    data_fixture.create_password_provider(enabled=True)
    enforce_single_sign_on()

    finish_flow(api_client, intercp, start_flow(api_client))

    user = get_user_model().objects.get(email="nerdy_koala@visionschool.dev")
    assert workspace.workspaceuser_set.get(user=user).permissions == "MEMBER"


@pytest.mark.django_db
def test_existing_users_join_default_workspace_keeping_roles(settings, data_fixture):
    admin = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin)
    other = data_fixture.create_user()
    inactive = data_fixture.create_user(is_active=False)
    settings.INTERCP_DEFAULT_WORKSPACE_ID = workspace.id

    add_to_default_workspace()

    members = dict(workspace.workspaceuser_set.values_list("user_id", "permissions"))
    assert members == {admin.id: "ADMIN", other.id: "MEMBER"}
    assert inactive.id not in members


@pytest.mark.django_db
def test_callback_links_existing_password_account(intercp, api_client, data_fixture):
    data_fixture.create_password_provider(enabled=True)
    user = data_fixture.create_user(email="nerdy_koala@visionschool.dev")
    enforce_single_sign_on()

    response = finish_flow(api_client, intercp, start_flow(api_client))

    assert "token" in parse_qs(urlsplit(response["Location"]).query)
    assert InterCPAuthProviderModel.objects.get().users.filter(id=user.id).exists()


@pytest.mark.django_db
def test_callback_rejects_wrong_state(intercp, api_client):
    start_flow(api_client)

    response = api_client.get(
        reverse("api:intercp_auth:callback"), {"state": "forged", "code": "x"}
    )

    assert error_of(response) == "invalid_state"


@pytest.mark.django_db
def test_callback_rejects_id_token_for_another_client(
    intercp, api_client, data_fixture
):
    data_fixture.create_password_provider(enabled=True)
    enforce_single_sign_on()
    params = start_flow(api_client)

    response = finish_flow(api_client, intercp, params, aud="another-client")

    assert error_of(response) == "provider_error"
    assert not get_user_model().objects.exists()


@pytest.mark.django_db
def test_callback_rejects_symmetric_id_token(intercp, api_client, data_fixture):
    data_fixture.create_password_provider(enabled=True)
    enforce_single_sign_on()
    params = start_flow(api_client)
    intercp.post(
        TOKEN,
        json={
            "access_token": "access",
            "token_type": "Bearer",
            "id_token": jwt.encode(
                {"iss": ISSUER, "aud": CLIENT_ID},
                CLIENT_SECRET,
                algorithm="HS256",
                headers={"kid": KID},
            ),
        },
    )

    response = api_client.get(
        reverse("api:intercp_auth:callback"),
        {"state": params["state"][0], "code": "the-code"},
    )

    assert error_of(response) == "provider_error"


@pytest.mark.django_db
def test_callback_rejects_unverified_email(intercp, api_client, data_fixture):
    data_fixture.create_password_provider(enabled=True)
    enforce_single_sign_on()
    params = start_flow(api_client)

    response = finish_flow(
        api_client, intercp, params, email="a@b.test", email_verified=False
    )

    assert error_of(response) == "unverified_email"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "original", ["//evil.test/x", "https://evil.test", "/\\evil"]
)
def test_original_cannot_redirect_off_site(
    intercp, api_client, data_fixture, original
):
    data_fixture.create_password_provider(enabled=True)
    enforce_single_sign_on()
    params = start_flow(api_client, f"?original={original}")

    response = finish_flow(api_client, intercp, params)

    url = urlsplit(response["Location"])
    assert f"{url.scheme}://{url.netloc}{url.path}" == FRONTEND + "/"


@pytest.mark.django_db
def test_password_login_is_blocked_for_staff_after_enforcement(
    intercp, api_client, data_fixture
):
    data_fixture.create_password_provider(enabled=True)
    data_fixture.create_user(email="admin@test.test", password="pw", is_staff=True)
    enforce_single_sign_on()

    response = api_client.post(
        reverse("api:user:token_auth"),
        {"email": "admin@test.test", "password": "pw"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["error"] == "ERROR_AUTH_PROVIDER_DISABLED"


@pytest.mark.django_db
def test_staff_can_add_a_user_to_a_workspace(api_client, data_fixture):
    _, token = data_fixture.create_user_and_token(is_staff=True)
    owner = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner)
    user = data_fixture.create_user()
    url = reverse("api:intercp_auth:admin_add_workspace_member")

    def add(user_id, permissions="MEMBER"):
        body = {
            "workspace_id": workspace.id,
            "user_id": user_id,
            "permissions": permissions,
        }
        return api_client.post(
            url,
            body,
            format="json",
            HTTP_AUTHORIZATION=f"JWT {token}",
        )

    response = add(user.id, "ADMIN")
    assert response.status_code == 200
    assert response.json()["added"] is True
    assert workspace.workspaceuser_set.get(user=user).permissions == "ADMIN"

    # An existing member keeps their role.
    response = add(owner.id)
    assert response.json() == {
        "workspace_id": workspace.id,
        "user_id": owner.id,
        "permissions": "ADMIN",
        "added": False,
    }


@pytest.mark.django_db
def test_only_staff_can_add_workspace_members(api_client, data_fixture):
    _, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace()
    user = data_fixture.create_user()

    response = api_client.post(
        reverse("api:intercp_auth:admin_add_workspace_member"),
        {"workspace_id": workspace.id, "user_id": user.id},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == 403
    assert not workspace.workspaceuser_set.filter(user=user).exists()
