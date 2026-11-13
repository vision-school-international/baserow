import secrets
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.signing import BadSignature
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse

from loguru import logger
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from baserow.core.auth_provider.exceptions import UnverifiedEmailFromProvider
from baserow.core.auth_provider.types import UserInfo
from baserow.core.exceptions import (
    FeatureDisabledException,
    WorkspaceInvitationDoesNotExist,
    WorkspaceInvitationEmailMismatch,
    WorkspaceInvitationLinkDoesNotExist,
    WorkspaceInvitationLinkSignupsDisabled,
)
from baserow.core.user.exceptions import DeactivatedUserException, DisabledSignupError
from baserow.core.user.utils import generate_session_tokens_for_user, sign_user_session

from . import oidc
from .models import InterCPAuthProviderModel
from .sync import add_to_default_workspace

SESSION_KEY = "intercp_auth"
ERROR_PAGE_PATH = "/login/intercp-error"

# Sign-in failures shown to the user; everything else is a generic failure.
SIGN_IN_ERRORS = {
    BadSignature: "invitation_invalid",
    UnverifiedEmailFromProvider: "unverified_email",
    DeactivatedUserException: "user_deactivated",
    DisabledSignupError: "signup_disabled",
    WorkspaceInvitationDoesNotExist: "invitation_invalid",
    WorkspaceInvitationEmailMismatch: "invitation_email_mismatch",
    WorkspaceInvitationLinkDoesNotExist: "invitation_invalid",
    WorkspaceInvitationLinkSignupsDisabled: "signup_disabled",
    # Raised when the invitation links feature flag is off.
    FeatureDisabledException: "invitation_invalid",
}


class LoginView(APIView):
    """Redirects the browser to InterCP to start the sign-in."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request: Request) -> HttpResponseRedirect:
        try:
            authorization_url, state = oidc.start(_callback_url())
        except (oidc.OIDCError, ImproperlyConfigured) as e:
            logger.warning("InterCP sign-in could not start: {}", e)
            return _error_redirect("provider_error")

        request.session[SESSION_KEY] = {
            "state": state,
            "original": _relative_path_or_none(request.GET.get("original")),
            "invitation_token": request.GET.get("workspace_invitation_token"),
            "invitation_link_slug": request.GET.get("workspace_invitation_link_slug"),
        }
        return HttpResponseRedirect(authorization_url)


class CallbackView(APIView):
    """Completes the sign-in when InterCP redirects back."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request: Request) -> HttpResponseRedirect:
        # Pop first: a flow can only be completed once.
        flow = request.session.pop(SESSION_KEY, None)
        state = request.GET.get("state", "")
        # Bytes, so a non-ASCII `state` compares unequal instead of raising.
        if flow is None or not secrets.compare_digest(
            state.encode(), flow["state"].encode()
        ):
            return _error_redirect("invalid_state")

        code = request.GET.get("code")
        if not code:
            # The user cancelled or InterCP refused, e.g. `error=access_denied`.
            return _error_redirect("cancelled")

        try:
            claims = oidc.finish(code, _callback_url())
        except oidc.OIDCError as e:
            logger.warning("InterCP sign-in failed: {}", e)
            return _error_redirect("provider_error")

        email = claims.get("email")
        if not email:
            return _error_redirect("missing_email")

        user_info = UserInfo(
            email=email,
            name=claims.get("name") or claims.get("preferred_username") or email,
            # Only an explicit true counts; core rejects anything else.
            email_verified=claims.get("email_verified") is True,
            workspace_invitation_token=flow["invitation_token"],
            workspace_invitation_link_slug=flow["invitation_link_slug"],
        )

        provider = InterCPAuthProviderModel.objects.filter(enabled=True).first()
        if provider is None:
            return _error_redirect("provider_error")

        try:
            with transaction.atomic():
                user, _ = provider.get_type().get_or_create_user_and_sign_in(
                    provider, user_info
                )
                add_to_default_workspace([user])
        except tuple(SIGN_IN_ERRORS) as e:
            return _error_redirect(_sign_in_error_code(e))

        return HttpResponseRedirect(_signed_in_url(user, flow["original"]))


def _callback_url() -> str:
    return urljoin(settings.PUBLIC_BACKEND_URL, reverse("api:intercp_auth:callback"))


def _relative_path_or_none(value: Optional[str]) -> Optional[str]:
    """Only same-site paths, so `original` cannot become an open redirect."""

    if (
        value
        and value.startswith("/")
        and not value.startswith("//")
        and "\\" not in value
    ):
        return value
    return None


def _sign_in_error_code(error: Exception) -> str:
    return next(
        code for cls, code in SIGN_IN_ERRORS.items() if isinstance(error, cls)
    )


def _frontend_url(path: str, params: dict) -> str:
    """The frontend URL for `path` with `params` added to any query it already has."""

    url = urlsplit(settings.PUBLIC_WEB_FRONTEND_URL.rstrip("/") + path)
    query = urlencode([*parse_qsl(url.query, keep_blank_values=True), *params.items()])
    return urlunsplit(url._replace(query=query))


def _signed_in_url(user, original: Optional[str]) -> str:
    tokens = generate_session_tokens_for_user(user, include_refresh_token=True)
    refresh_token = tokens["refresh_token"]
    return _frontend_url(
        original or "/",
        {
            "token": refresh_token,
            "user_session": sign_user_session(user.id, refresh_token),
        },
    )


def _error_redirect(code: str) -> HttpResponseRedirect:
    return HttpResponseRedirect(_frontend_url(ERROR_PAGE_PATH, {"error": code}))
