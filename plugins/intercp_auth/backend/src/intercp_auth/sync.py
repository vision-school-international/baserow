from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from loguru import logger

from baserow.core.auth_provider.handler import (
    AuthProviderHandler,
    PasswordProviderHandler,
)
from baserow.core.handler import CoreHandler
from baserow.core.models import WORKSPACE_USER_PERMISSION_MEMBER, Workspace
from baserow.core.registries import auth_provider_type_registry

from . import oidc
from .auth_provider_types import InterCPAuthProviderType


@transaction.atomic
def enforce_single_sign_on() -> None:
    """
    Makes InterCP the only way in. Safe to run any number of times:
    - exactly one InterCP provider exists and is enabled,
    - the password provider is disabled,
    - no account keeps a password,
    - the first-run admin signup page is off (it only offers password signup; the
      first InterCP user becomes staff anyway).

    Raises ImproperlyConfigured before changing anything if InterCP is not configured,
    so a missing setting cannot lock everyone out.
    """

    oidc.check_configured()

    provider_type = auth_provider_type_registry.get(InterCPAuthProviderType.type)
    provider = provider_type.model_class.objects.first()
    if provider is None:
        AuthProviderHandler.create_auth_provider(None, provider_type, enabled=True)
    elif not provider.enabled:
        AuthProviderHandler.update_auth_provider(None, provider, enabled=True)

    password_provider = PasswordProviderHandler.get()
    if password_provider.enabled:
        AuthProviderHandler.update_auth_provider(None, password_provider, enabled=False)

    # Core marks SSO-only accounts with an empty password (e.g. 2FA is refused for
    # them), so use that rather than Django's unusable-password marker.
    get_user_model().objects.exclude(password="").update(password="")

    instance_settings = CoreHandler().get_settings()
    if instance_settings.show_admin_signup_page:
        instance_settings.show_admin_signup_page = False
        instance_settings.save(update_fields=["show_admin_signup_page"])


def add_to_default_workspace(users=None) -> None:
    """
    Adds users to INTERCP_DEFAULT_WORKSPACE_ID as members, through core's
    add_user_to_workspace, which never changes an existing member's role
    (core/handler.py:1587-1604). Each user is added once, recorded in
    DefaultWorkspaceJoin, so someone a staff member removed stays removed.

    :param users: The users to add; all active users when None.
    """

    from .models import DefaultWorkspaceJoin

    workspace_id = settings.INTERCP_DEFAULT_WORKSPACE_ID
    if workspace_id is None:
        return
    workspace = Workspace.objects.filter(id=workspace_id).first()
    if workspace is None:
        # Workspace.objects leaves out trashed workspaces.
        logger.warning(f"INTERCP_DEFAULT_WORKSPACE_ID {workspace_id} not found.")
        return
    joined = DefaultWorkspaceJoin.objects.filter(workspace=workspace)
    if users is None:
        # One query: on a normal start everyone has a record and nothing loads.
        users = (
            get_user_model()
            .objects.filter(is_active=True)
            .exclude(id__in=joined.values("user_id"))
        )
    else:
        joined_ids = set(
            joined.filter(user__in=users).values_list("user_id", flat=True)
        )
        users = [user for user in users if user.id not in joined_ids]
    handler = CoreHandler()
    for user in users:
        # An existing member keeps their role and only gets the record.
        handler.add_user_to_workspace(
            workspace, user, permissions=WORKSPACE_USER_PERMISSION_MEMBER
        )
        DefaultWorkspaceJoin.objects.get_or_create(user=user, workspace=workspace)
