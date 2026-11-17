import re
from typing import Dict

from django.conf import settings

from baserow.contrib.builder.domains.exceptions import SubDomainHasInvalidDomainName
from baserow.contrib.builder.domains.registries import DomainType

from .models import PathDomain

# One lowercase DNS label: it's both the URL's first path segment and a label of
# the stored domain name.
SLUG = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


# shortcut: any domain named "<slug>.<host>" is served at /<slug>, because the
# public lookup is by name only: a custom domain (or a subdomain, if the host is
# in BASEROW_BUILDER_DOMAINS) of that name takes the path, and one named <host>
# takes the bare host. Add checks to those types if people outside the team ever
# create domains.
class PathDomainType(DomainType):
    type = "path"
    model_class = PathDomain

    def prepare_values(self, values: Dict) -> Dict:
        domain_name = values.get("domain_name", None)
        if domain_name is not None:
            self._validate_domain_name(domain_name)
        return values

    def _validate_domain_name(self, domain_name: str):
        """
        Only "<slug>.<BASEROW_APP_PATHS_HOST>", with a slug of one DNS label.

        :raises SubDomainHasInvalidDomainName: Otherwise, like a subdomain outside
            BASEROW_BUILDER_DOMAINS, so the API answers the same 400.
        """

        host = settings.BASEROW_APP_PATHS_HOST
        slug, _, rest = domain_name.partition(".")
        # fullmatch: match's $ also matches before a final newline.
        if host and rest == host and SLUG.fullmatch(slug):
            return

        error = SubDomainHasInvalidDomainName(domain_name)
        error.available_domain_names = [f"<slug>.{host}"] if host else []
        raise error
