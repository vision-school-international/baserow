"""
InterCP (Authentik) OpenID Connect sign-in, following Baserow's own OpenID Connect
provider (enterprise sso/oauth2/auth_provider_types.py): requests_oauthlib's
OAuth2Session for the authorization code flow, and the ID token verified with the
provider's JWKS fetched through requests.
"""

from functools import cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

import jwt
import requests
from jwt.algorithms import RSAAlgorithm
from requests_oauthlib import OAuth2Session

from baserow.core.cache import global_cache

HTTP_TIMEOUT_SECONDS = 60
SCOPE = ["openid", "email", "profile"]
JWKS_CACHE_SECONDS = 3600


class OIDCError(Exception):
    """InterCP could not be reached or its response failed validation."""


def check_configured() -> None:
    missing = [
        name
        for name in (
            "INTERCP_OIDC_ISSUER",
            "INTERCP_OIDC_CLIENT_ID",
            "INTERCP_OIDC_CLIENT_SECRET",
        )
        if not getattr(settings, name, "")
    ]
    if missing:
        raise ImproperlyConfigured(f"Missing settings: {', '.join(missing)}")


@cache
def _wellknown(issuer: str) -> dict:
    """Authentik's discovery document, as enterprise get_wellknown_urls reads it."""

    try:
        document = requests.get(
            f"{issuer.rstrip('/')}/.well-known/openid-configuration",
            timeout=HTTP_TIMEOUT_SECONDS,
        ).json()
        return {
            "authorization_url": document["authorization_endpoint"],
            "access_token_url": document["token_endpoint"],
            "jwks_url": document["jwks_uri"],
            "issuer": document["issuer"],
        }
    except Exception as e:
        raise OIDCError(f"Discovery failed: {e}") from e


def _session(redirect_uri: str) -> OAuth2Session:
    return OAuth2Session(
        settings.INTERCP_OIDC_CLIENT_ID, redirect_uri=redirect_uri, scope=SCOPE
    )


def start(redirect_uri: str) -> tuple[str, str]:
    """Returns the InterCP authorization URL and the state to keep in the session."""

    check_configured()
    urls = _wellknown(settings.INTERCP_OIDC_ISSUER)
    return _session(redirect_uri).authorization_url(urls["authorization_url"])


def finish(code: str, redirect_uri: str) -> dict:
    """Exchanges the code and returns the verified ID token claims."""

    check_configured()
    urls = _wellknown(settings.INTERCP_OIDC_ISSUER)
    try:
        token = _session(redirect_uri).fetch_token(
            urls["access_token_url"],
            code=code,
            client_secret=settings.INTERCP_OIDC_CLIENT_SECRET,
        )
    except Exception as e:
        raise OIDCError(f"Token exchange failed: {e}") from e

    if "id_token" not in token:
        raise OIDCError("Id token is missing")

    try:
        return jwt.decode(
            token["id_token"],
            key=_verifying_key(urls["jwks_url"], token["id_token"]),
            algorithms=["RS256"],
            audience=settings.INTERCP_OIDC_CLIENT_ID,
            issuer=urls["issuer"],
        )
    except jwt.InvalidTokenError as e:
        raise OIDCError(f"Invalid ID token: {e}") from e


def _verifying_key(jwks_url: str, id_token: str, retry_on_fail: bool = True):
    """Enterprise _get_verifying_key: cached JWKS, refetched once on a missing kid."""

    cache_key = f"intercp_auth_jwks_{jwks_url}"
    try:
        jwks = global_cache.get(
            cache_key,
            default=lambda: requests.get(jwks_url, timeout=HTTP_TIMEOUT_SECONDS).json(),
            timeout=JWKS_CACHE_SECONDS,
        )
    except Exception as e:
        raise OIDCError(f"Failed to call JWK endpoint {jwks_url}: {e}") from e

    kid = jwt.get_unverified_header(id_token).get("kid")
    for jwk in jwks.get("keys", []):
        if jwk.get("kid") == kid:
            return RSAAlgorithm.from_jwk(jwk)

    if retry_on_fail:
        # The keys might have rotated, try again without the cache.
        global_cache.invalidate(cache_key)
        return _verifying_key(jwks_url, id_token, False)
    raise OIDCError("No JWK matches the ID token's key id")
