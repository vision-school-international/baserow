from django.core.exceptions import ValidationError
from django.db import models
from django.urls import include, path

from rest_framework import serializers

from baserow.contrib.database.fields.field_types import TextFieldType
from baserow.contrib.database.fields.registries import field_type_registry

from .flight import clean_flight
from .models import REFRESH_CHOICES, REFRESH_VIEW, FlightField


def _check_refresh(value):
    if value not in dict(REFRESH_CHOICES):
        raise ValidationError(f"'{value}' isn't view or schedule.", code="invalid")


class FlightFieldType(TextFieldType):
    """
    A flight number, stored as upper case text, so the cells, filters and sorting
    are the core text ones. Its live status comes from AirLabs (flight.py) and is
    shown next to it.
    """

    type = "flight"
    model_class = FlightField
    allowed_fields = ["flight_refresh"]
    serializer_field_names = list(allowed_fields)
    serializer_field_overrides = {
        "flight_refresh": serializers.ChoiceField(
            choices=REFRESH_CHOICES,
            required=False,
            help_text="Look the flights up when they're viewed (view) or every few "
            "minutes (schedule).",
        ),
    }

    def get_api_urls(self):
        from . import urls

        # /api/database/fields/flight-tracker/ (database/api/fields/urls.py).
        return [path("flight-tracker/", include(urls, namespace="flight_tracker"))]

    # The serializer's choices only cover API requests; these hooks also cover the
    # handler calls of the agent's field tools (database/tools/fields.py).
    def before_create(
        self, table, primary, allowed_field_values, order, user, field_kwargs
    ):
        _check_refresh(allowed_field_values.get("flight_refresh", REFRESH_VIEW))

    def before_update(self, from_field, to_field_values, user, field_kwargs):
        if "flight_refresh" in to_field_values:
            _check_refresh(to_field_values["flight_refresh"])

    # No default value: a column default would skip the check, like field_patterns'
    # NoTextDefaultMixin (a text field converted to this type keeps text_default).
    def get_serializer_field(self, instance, **kwargs):
        return super().get_serializer_field(instance, **{"default": None, **kwargs})

    def get_model_field(self, instance, **kwargs):
        return models.TextField(
            default=None, blank=True, null=True, db_index=instance.db_index, **kwargs
        )

    def get_compatible_filter_field_type(self, field):
        return field_type_registry.get(TextFieldType.type)

    def prepare_value_for_db(self, instance, value):
        return clean_flight(value)

    def random_value(self, instance, fake, cache):
        return ""
