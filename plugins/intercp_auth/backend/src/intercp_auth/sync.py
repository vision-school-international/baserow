from django.contrib.auth import get_user_model
from django.db import transaction

from baserow.core.auth_provider.handler import (
    AuthProviderHandler,
    PasswordProviderHandler,
)
from baserow.core.handler import CoreHandler
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
