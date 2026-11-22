from django.db.models import Q

from baserow.contrib.database.views.registries import ViewFilterType

# The flight tracker's statuses (tracker.py to_cell), plus its two errors.
STATUSES = {"scheduled", "en-route", "landed"}
ERRORS = {"not_found", "invalid_flight_number"}


class FlightStatusViewFilterType(ViewFilterType):
    """
    Rows whose flight tracker has a status ("scheduled", "en-route", "landed"),
    an error ("not_found", "invalid_flight_number"), or no data yet ("none").
    Like core's HasFileTypeViewFilterType, an unknown value filters nothing.
    """

    type = "flight_status"
    compatible_field_types = ["flight_tracker"]

    def get_filter(self, field_name, value, model_field, field):
        value = value.strip()
        if value in STATUSES:
            return Q(**{f"{field_name}__status": value})
        if value in ERRORS:
            return Q(**{f"{field_name}__error": value})
        if value == "none":
            # `__status=None` matches JSON null; `__status__isnull` would only
            # match a missing key, and to_cell always writes the key.
            return Q(**{f"{field_name}__isnull": True}) | Q(
                **{f"{field_name}__status": None, f"{field_name}__error": None}
            )
        return Q()
