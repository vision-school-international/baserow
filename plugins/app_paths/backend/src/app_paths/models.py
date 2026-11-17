from urllib.parse import urlparse

from django.conf import settings

from baserow.contrib.builder.domains.models import Domain


class PathDomain(Domain):
    """
    A site published at https://<host>/<slug>, where <host> is
    BASEROW_APP_PATHS_HOST. Its domain_name is "<slug>.<host>": a valid, unique
    name that core's domain lookup (get_public_builder_by_domain_name) finds as is.

    Don't uninstall the plugin while path domains exist: their rows would be left
    without a model, which breaks listing that builder's domains and deleting it.
    Delete the path domains first.
    """

    @property
    def slug(self):
        return self.domain_name.split(".", 1)[0]

    def get_public_url(self):
        # Like Domain.get_public_url, with the host and the slug as its path.
        parsed_url = urlparse(settings.PUBLIC_WEB_FRONTEND_URL)
        port_string = f":{parsed_url.port}" if parsed_url.port else ""
        host = self.domain_name.split(".", 1)[1]
        return f"{parsed_url.scheme}://{host}{port_string}/{self.slug}"
