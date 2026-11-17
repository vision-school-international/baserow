from django.apps import AppConfig


class AppPathsConfig(AppConfig):
    name = "app_paths"

    def ready(self):
        # Same registration as core's domain types (contrib/builder/apps.py).
        from baserow.contrib.builder.domains.registries import domain_type_registry

        from .domain_types import PathDomainType

        domain_type_registry.register(PathDomainType())
