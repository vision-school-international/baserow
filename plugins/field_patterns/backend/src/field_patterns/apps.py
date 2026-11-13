from django.apps import AppConfig


class FieldPatternsConfig(AppConfig):
    name = "field_patterns"

    def ready(self):
        # Same registration as core (contrib/database/apps.py).
        from baserow.contrib.database.fields.registries import field_type_registry

        from .field_types import PatternTextFieldType

        field_type_registry.register(PatternTextFieldType())
