from django.apps import AppConfig


class FlightTrackerConfig(AppConfig):
    name = "flight_tracker"

    def ready(self):
        # Same registration as core (contrib/database/apps.py).
        from baserow.contrib.database.fields.registries import field_type_registry
        from baserow.contrib.database.views.registries import (
            view_filter_type_registry,
        )

        from .field_types import FlightFieldType, FlightTrackerFieldType
        from .view_filters import FlightStatusViewFilterType

        field_type_registry.register(FlightFieldType())
        field_type_registry.register(FlightTrackerFieldType())
        view_filter_type_registry.register(FlightStatusViewFilterType())
