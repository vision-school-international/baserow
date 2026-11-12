from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


class InterCPAuthConfig(AppConfig):
    name = "intercp_auth"

    def ready(self):
        from baserow.core.registries import auth_provider_type_registry

        from .auth_provider_types import InterCPAuthProviderType

        auth_provider_type_registry.register(InterCPAuthProviderType())
        # Baserow runs `migrate` on every start, so this keeps the rules enforced.
        post_migrate.connect(_enforce_single_sign_on, sender=self)


def _enforce_single_sign_on(sender, **kwargs):
    # The test database is migrated before any test can configure InterCP; the tests
    # call enforce_single_sign_on themselves.
    if settings.TESTS:
        return

    from .sync import enforce_single_sign_on

    enforce_single_sign_on()
