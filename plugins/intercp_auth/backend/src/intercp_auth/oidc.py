"""
A minimal OpenID Connect client for the authorization code flow with PKCE.

It knows nothing about Baserow: `start` builds the redirect to the identity provider,
`finish` exchanges the code and returns the verified user claims.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from functools import cache
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

import jwt
import requests

HTTP_TIMEOUT_SECONDS = 10
# Asymmetric only: an HS256 token would be signed with the client secret, which this
# server also holds, so it would not prove the token came from the provider.
ID_TOKEN_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
SCOPES = "openid email profile"


class OIDCError(Exception):
    """The identity provider could not be reached or its response failed validation."""


@dataclass(frozen=True)
class Provider:
    issuer: str
    client_id: str
    client_secret: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks: jwt.PyJWKClient


@dataclass(frozen=True)
class AuthorizationRequest:
    url: str
    state: str
    nonce: str
    code_verifier: str


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


def get_provider() -> Provider:
    check_configured()
    return _discover(
        settings.INTERCP_OIDC_ISSUER,
        settings.INTERCP_OIDC_CLIENT_ID,
        settings.INTERCP_OIDC_CLIENT_SECRET,
    )


@cache
def _discover(issuer: str, client_id: str, client_secret: str) -> Provider:
    # A failed discovery raises, and functools.cache does not store exceptions, so the
    # next sign-in retries.
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    document = _get_json(url)
    if document.get("issuer") != issuer:
        raise OIDCError("Discovery issuer does not match the configured issuer.")
    try:
        return Provider(
            issuer=issuer,
            client_id=client_id,
            client_secret=client_secret,
            authorization_endpoint=document["authorization_endpoint"],
            token_endpoint=document["token_endpoint"],
            userinfo_endpoint=document["userinfo_endpoint"],
            jwks=jwt.PyJWKClient(document["jwks_uri"], timeout=HTTP_TIMEOUT_SECONDS),
        )
    except KeyError as e:
        raise OIDCError(f"Discovery document is missing {e}.") from e


def start(redirect_uri: str) -> AuthorizationRequest:
    provider = get_provider()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    query = urlencode(
        {
            "response_type": "code",
            "client_id": provider.client_id,
            "redirect_uri": redirect_uri,
            "scope": SCOPES,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return AuthorizationRequest(
        url=f"{provider.authorization_endpoint}?{query}",
        state=state,
        nonce=nonce,
        code_verifier=code_verifier,
    )


def finish(code: str, redirect_uri: str, nonce: str, code_verifier: str) -> dict:
    """
    Exchanges the authorization code and returns the userinfo claims, after verifying
    the ID token (signature, issuer, audience, expiry, nonce) and that the userinfo
    belongs to the same subject.
    """

    provider = get_provider()
    tokens = _post_json(
        provider.token_endpoint,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
        },
    )
    id_token = tokens.get("id_token")
    access_token = tokens.get("access_token")
    if not id_token or not access_token:
        raise OIDCError("Token response is missing id_token or access_token.")

    try:
        signing_key = provider.jwks.get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key,
            algorithms=ID_TOKEN_ALGORITHMS,
            audience=provider.client_id,
            issuer=provider.issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "nonce"]},
        )
    except jwt.PyJWTError as e:
        raise OIDCError(f"Invalid ID token: {e}") from e

    if not secrets.compare_digest(str(claims["nonce"]), nonce):
        raise OIDCError("ID token nonce does not match.")

    userinfo = _get_json(
        provider.userinfo_endpoint,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if userinfo.get("sub") != claims["sub"]:
        raise OIDCError("Userinfo subject does not match the ID token.")
    return userinfo


def _get_json(url: str, headers: dict | None = None) -> dict:
    try:
        response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as e:
        raise OIDCError(f"GET {url} failed: {e}") from e


def _post_json(url: str, data: dict) -> dict:
    try:
        response = requests.post(url, data=data, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as e:
        raise OIDCError(f"POST {url} failed: {e}") from e
