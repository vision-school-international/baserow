import json

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Value
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.db.models.functions import Concat
from django.urls import include, path

from rest_framework import serializers

from baserow.contrib.database.api.fields.errors import (
    ERROR_FIELD_NOT_IN_TABLE,
    ERROR_INCOMPATIBLE_FIELD,
)
from baserow.contrib.database.fields.dependencies.handler import (
    FieldDependencyHandler,
)
from baserow.contrib.database.fields.dependencies.models import FieldDependency
from baserow.contrib.database.fields.exceptions import (
    FieldNotInTable,
    IncompatibleField,
)
from baserow.contrib.database.fields.field_sortings import OptionallyAnnotatedOrderBy
from baserow.contrib.database.fields.field_types import TextFieldType
from baserow.contrib.database.fields.models import Field
from baserow.contrib.database.fields.registries import (
    ReadOnlyFieldType,
    field_type_registry,
)

from .flight import clean_flight
from .models import (
    MAX_INTERVAL_MINUTES,
    MIN_INTERVAL_MINUTES,
    REFRESH_CHOICES,
    REFRESH_VIEW,
    FlightField,
    FlightStatus,
    FlightTrackerField,
)
from .tracker import CODE_FIELD_TYPES, summary


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


class FlightTrackerFieldType(ReadOnlyFieldType):
    """
    Read-only JSON with the live AirLabs data of the flight number in another
    field of the row (tracker.py to_cell), for people and for apps. Nobody can
    set it: its cells are written by tracker.py as the user who set it up.
    """

    type = "flight_tracker"
    model_class = FlightTrackerField
    can_be_in_form_view = False
    # Duplicating a table keeps the data instead of looking every flight up again.
    keep_data_on_duplication = True
    # `flight_tracker_user_id` is set here, never by a request; it must be allowed
    # so `set_allowed_attrs` applies it (like ai_tables' ai_auto_update_user_id).
    serializer_field_names = [
        "flight_code_field_id",
        "flight_refresh",
        "flight_interval_minutes",
    ]
    allowed_fields = serializer_field_names + ["flight_tracker_user_id"]
    serializer_field_overrides = {
        "flight_code_field_id": serializers.IntegerField(
            required=False,
            allow_null=True,
            min_value=1,
            help_text="The text field of the same table holding the flight number.",
        ),
        "flight_refresh": serializers.ChoiceField(
            choices=REFRESH_CHOICES,
            required=False,
            help_text="Look the flights up when they're viewed (view) or every "
            "flight_interval_minutes (schedule).",
        ),
        "flight_interval_minutes": serializers.IntegerField(
            required=False,
            min_value=MIN_INTERVAL_MINUTES,
            max_value=MAX_INTERVAL_MINUTES,
            help_text="How old a row's flight data may get before it's looked up "
            "again.",
        ),
    }
    api_exceptions_map = {
        FieldNotInTable: ERROR_FIELD_NOT_IN_TABLE,
        IncompatibleField: ERROR_INCOMPATIBLE_FIELD,
    }

    def can_be_primary_field(self, field_or_values):
        return False

    def _validate(self, table, values, current=None):
        """The serializer only covers API requests; this also covers the handler
        calls of the agent's field tools (database/tools/fields.py)."""

        def value(name, default=None):
            return values.get(name, getattr(current, name, default))

        _check_refresh(value("flight_refresh", REFRESH_VIEW))
        interval = value("flight_interval_minutes", 30)
        if not (
            isinstance(interval, int)
            and MIN_INTERVAL_MINUTES <= interval <= MAX_INTERVAL_MINUTES
        ):
            raise ValidationError(
                f"The interval must be {MIN_INTERVAL_MINUTES} to "
                f"{MAX_INTERVAL_MINUTES} minutes.",
                code="invalid",
            )
        code_field_id = value("flight_code_field_id")
        if code_field_id is not None:
            code_field = Field.objects.filter(id=code_field_id, table=table).first()
            if code_field is None:
                raise FieldNotInTable(
                    f"The field {code_field_id} is not in table {table.id}."
                )
            if code_field.get_type().type not in CODE_FIELD_TYPES:
                raise IncompatibleField(
                    f"The field {code_field_id} can't hold flight numbers."
                )

    def before_create(
        self, table, primary, allowed_field_values, order, user, field_kwargs
    ):
        self._validate(table, allowed_field_values)
        allowed_field_values["flight_tracker_user_id"] = user.id if user else None

    def before_update(self, from_field, to_field_values, user, field_kwargs):
        current = from_field if isinstance(from_field, FlightTrackerField) else None
        self._validate(from_field.table, to_field_values, current)
        # Whoever changes the settings is who the data is written as from now on.
        to_field_values["flight_tracker_user_id"] = user.id if user else None

    def _fill_later(self, field):
        from .tasks import fill_tracker

        transaction.on_commit(lambda: fill_tracker.delay(field.id))

    def after_create(self, field, model, user, connection, before, field_kwargs):
        self._fill_later(field)

    def after_update(
        self,
        from_field,
        to_field,
        from_model,
        to_model,
        user,
        connection,
        altered_column,
        before,
        to_field_kwargs,
    ):
        if not isinstance(from_field, FlightTrackerField):
            # Converted into a tracker: its cells are empty (get_alter_column_
            # prepare_new_value), so lookups of an earlier tracker don't count.
            FlightStatus.objects.filter(field=to_field).delete()
        self._fill_later(to_field)

    def get_model_field(self, instance, **kwargs):
        return models.JSONField(default=None, null=True, blank=True, **kwargs)

    def get_serializer_field(self, instance, **kwargs):
        # Core passes help_text (get_serializer_help_text) in kwargs.
        return serializers.JSONField(
            **{"required": False, "allow_null": True, **kwargs}
        )

    def get_serializer_help_text(self, instance):
        return (
            "Read only. The live AirLabs data of the flight number in the field "
            "flight_code_field_id: status, airline, departure and arrival (airport, "
            "terminal, gate, scheduled, estimated and actual times), or null."
        )

    def get_response_serializer_field(self, instance, **kwargs):
        return self.get_serializer_field(instance, **kwargs)

    # Converting a field to this type drops its values, like core's read-only
    # LastModifiedBy (field_types.py): text isn't flight data. Converting from it
    # keeps the JSON as text.
    def get_alter_column_prepare_new_value(self, connection, from_field, to_field):
        return "p_in = NULL;", {}

    # Search the flight's details, not the JSON's keys ("gate", "arrival"), which
    # every filled cell holds.
    def get_search_expression(self, field, queryset):
        column = field.db_column
        parts = [
            KeyTextTransform("flight", column),
            KeyTextTransform("status", column),
            KeyTextTransform("airline_name", column),
            KeyTextTransform("airport_iata", KeyTransform("departure", column)),
            KeyTextTransform("airport_iata", KeyTransform("arrival", column)),
        ]
        spaced = [p for part in parts for p in (part, Value(" "))][:-1]
        return Concat(*spaced, output_field=models.TextField())

    def get_export_value(self, value, field_object, rich_value=False):
        if rich_value or value is None:
            return value
        return json.dumps(value, ensure_ascii=False)

    def get_human_readable_value(self, value, field_object):
        if not value:
            return ""
        return summary(value)

    # Sorted by the scheduled departure, in UTC: earliest flight first.
    def get_order(
        self, field, field_name, order_direction, sort_type, table_model=None
    ) -> OptionallyAnnotatedOrderBy:
        departure = KeyTextTransform(
            "scheduled_utc", KeyTransform("departure", field_name)
        )
        # Like core's CollationSortMixin: empty cells first ascending, last
        # descending. ISO "YYYY-MM-DD HH:MM" sorts in time order as text.
        if order_direction == "ASC":
            order = departure.asc(nulls_first=True)
        else:
            order = departure.desc(nulls_last=True)
        return OptionallyAnnotatedOrderBy(order=order)

    def get_field_dependencies(self, field_instance, field_cache):
        code_field_id = field_instance.flight_code_field_id
        if code_field_id is None:
            return []
        code_field = Field.objects_and_trash.filter(id=code_field_id).first()
        if code_field is None:
            return []
        if code_field.trashed:
            # Kept by name so restoring the field re-links it, like ai_tables.
            return [
                FieldDependency(
                    dependant=field_instance,
                    broken_reference_field_name=code_field.name,
                )
            ]
        return [FieldDependency(dependant=field_instance, dependency_id=code_field.id)]

    def _fill_rows_later(self, field, starting_row, via_path, context):
        # Only this table's own rows: a changed flight number is looked up at once.
        if context.depth != 0 or via_path:
            return
        rows = starting_row if isinstance(starting_row, list) else [starting_row]
        from .tasks import fill_tracker

        row_ids = [row.id for row in rows]
        transaction.on_commit(lambda: fill_tracker.delay(field.id, row_ids))

    def row_of_dependency_created(
        self,
        field,
        starting_row,
        update_collector,
        field_cache,
        via_path_to_starting_table,
        dependency_context,
    ):
        self._fill_rows_later(
            field, starting_row, via_path_to_starting_table, dependency_context
        )

    def row_of_dependency_updated(
        self,
        field,
        starting_row,
        update_collector,
        field_cache,
        via_path_to_starting_table,
        dependency_context,
    ):
        self._fill_rows_later(
            field, starting_row, via_path_to_starting_table, dependency_context
        )

    def row_of_dependency_deleted(self, *args, **kwargs):
        return

    def import_serialized(
        self,
        table,
        serialized_values,
        import_export_config,
        id_mapping,
        deferred_fk_update_collector,
    ):
        values = serialized_values.copy()
        # The code field may not exist yet; it's set once all fields are imported.
        code_field_id = values.pop("flight_code_field_id", None)
        # The user may not be a member where this is imported to; the data is
        # written again once someone saves the field's settings.
        values.pop("flight_tracker_user_id", None)
        field = super().import_serialized(
            table,
            values,
            import_export_config,
            id_mapping,
            deferred_fk_update_collector,
        )
        if code_field_id is not None:
            deferred_fk_update_collector.add_deferred_fk_to_update(
                field, "flight_code_field_id", code_field_id, "database_fields"
            )
        return field

    def after_import_serialized(self, field, field_cache, id_mapping):
        FieldDependencyHandler.rebuild_dependencies([field], field_cache)
        super().after_import_serialized(field, field_cache, id_mapping)

    def random_value(self, instance, fake, cache):
        return None
