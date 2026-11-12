from typing import Any, Dict, Optional
from urllib.parse import urljoin

from django.conf import settings
from django.urls import include, path, reverse

from baserow.core.auth_provider.auth_provider_types import AuthProviderType

from .models import InterCPAuthProviderModel


class InterCPAuthProviderType(AuthProviderType):
    """
    Signs users in through InterCP. There is exactly one provider row, created by
    `enforce_single_sign_on`, so it can neither be added nor deleted through the API.
    """

    type = "intercp"
    model_class = InterCPAuthProviderModel

    def get_api_urls(self):
        from . import urls

        return [path("intercp/", include(urls, namespace="intercp_auth"))]

    def can_create_new_providers(self, **kwargs) -> bool:
        return not self.model_class.objects.exists()

    def can_delete_existing_providers(self) -> bool:
        return False

    def get_login_options(self, **kwargs) -> Optional[Dict[str, Any]]:
        if not self.model_class.objects.filter(enabled=True).exists():
            return None

        login_url = urljoin(
            settings.PUBLIC_BACKEND_URL, reverse("api:intercp_auth:login")
        )
        return {
            "type": self.type,
            "items": [
                {
                    "type": self.type,
                    "name": settings.INTERCP_OIDC_NAME,
                    "redirect_url": login_url,
                }
            ],
            # The login page sends users straight here when it is the only option.
            "default_redirect_url": login_url,
        }
