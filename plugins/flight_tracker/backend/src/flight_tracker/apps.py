from django.apps import AppConfig


class FlightTrackerConfig(AppConfig):
    name = "flight_tracker"

    def ready(self):
        # Same registration as core (contrib/database/apps.py).
        from baserow.contrib.database.fields.registries import field_type_registry

        from .field_types import FlightFieldType

        field_type_registry.register(FlightFieldType())
