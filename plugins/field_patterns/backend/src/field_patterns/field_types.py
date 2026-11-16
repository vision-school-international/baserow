from django.core.exceptions import ValidationError
from django.db import models
from django.urls import include, path

from rest_framework import serializers

from baserow.contrib.database.fields.field_types import TextFieldType
from baserow.contrib.database.fields.registries import field_type_registry

from .models import (
    CASE_CHOICES,
    PATTERN_MAX_LENGTH,
    TIME_FORMAT_CHOICES,
    InternationalPhoneField,
    PatternTextField,
    TelegramUsernameField,
    TimeOfDayField,
)
from .patterns import check_pattern, clean_value
from .phones import COUNTRIES, check_country, clean_phone
from .telegram import CONVERT_SQL as TELEGRAM_CONVERT_SQL
from .telegram import clean_telegram_username
from .times import CONVERT_SQL as TIME_CONVERT_SQL
from .times import clean_time


def _check_required_pattern(pattern):
    # An empty pattern would turn down every value that isn't empty.
    if not pattern:
        raise ValidationError("A pattern is required.", code="required")
    check_pattern(pattern)


class NoTextDefaultMixin:
    """
    Ignores `text_default`. A text field converted to one of these types keeps
    its default (core TextField column), and core's TextFieldType would still give
    it to new rows: unchecked in the database, or refused by the check, so every
    new row failed.
    """

    def get_serializer_field(self, instance, **kwargs):
        # Core spreads kwargs last (TextFieldType.get_serializer_field).
        return super().get_serializer_field(instance, **{"default": None, **kwargs})

    def get_model_field(self, instance, **kwargs):
        # Core's TextFieldType.get_model_field without the default; it passes
        # `default=` itself, so it can't be overridden through super().
        return models.TextField(
            default=None,
            blank=True,
            null=True,
            db_index=instance.db_index,
            **kwargs,
        )


class PatternTextFieldType(NoTextDefaultMixin, TextFieldType):
    """
    Single line text that must match the field's regular expression. The cells,
    filters and sorting are the core text ones.

    Unlike core's TextFieldMatchingRegexFieldType (field_types.py), the pattern is
    per field and written by users, so it's never put into SQL: converting a field to
    this type keeps the existing values, and only new values are checked.
    """

    type = "pattern_text"
    model_class = PatternTextField
    # No default value: a column default would skip the check.
    allowed_fields = [
        "pattern",
        "pattern_error_message",
        "pattern_trim",
        "pattern_case",
    ]
    serializer_field_names = list(allowed_fields)
    serializer_field_overrides = {
        "pattern": serializers.CharField(
            max_length=PATTERN_MAX_LENGTH,
            validators=[check_pattern],
            help_text="The regular expression the whole value must match.",
        ),
        "pattern_error_message": serializers.CharField(
            max_length=255,
            required=False,
            allow_blank=True,
            help_text="Shown when a value doesn't match. A default is used if empty.",
        ),
        "pattern_trim": serializers.BooleanField(
            required=False,
            help_text="Remove spaces around the value before checking it.",
        ),
        "pattern_case": serializers.ChoiceField(
            choices=CASE_CHOICES,
            required=False,
            help_text="Change the value to lower or upper case before checking it.",
        ),
    }

    def get_api_urls(self):
        from . import urls

        # /api/database/fields/field-patterns/ (database/api/fields/urls.py), for both
        # of the plugin's field types.
        return [path("field-patterns/", include(urls, namespace="field_patterns"))]

    # The serializer checks the pattern only for API requests; these hooks also cover
    # the handler calls of the agent's field tools (database/tools/fields.py).
    def before_create(
        self, table, primary, allowed_field_values, order, user, field_kwargs
    ):
        _check_required_pattern(allowed_field_values.get("pattern"))

    def before_update(self, from_field, to_field_values, user, field_kwargs):
        if "pattern" in to_field_values or not isinstance(from_field, PatternTextField):
            _check_required_pattern(to_field_values.get("pattern"))

    # View filters treat it as text, like ai_tables' compatible_filter_type.
    def get_compatible_filter_field_type(self, field):
        return field_type_registry.get(TextFieldType.type)

    def get_serializer_field(self, instance, **kwargs):
        # DRF trims by default (rest_framework/fields.py:729); pattern_trim decides.
        return super().get_serializer_field(
            instance, **{"trim_whitespace": False, **kwargs}
        )

    def prepare_value_for_db(self, instance, value):
        # Every write path runs this. The row and form views send the error's
        # message as the detail (api/rows/views.py, api/views/form/views.py).
        return clean_value(instance, value)

    def random_value(self, instance, fake, cache):
        return ""


class InternationalPhoneFieldType(NoTextDefaultMixin, TextFieldType):
    """
    A phone number of any country. Numbers typed without + and a country code are
    read as numbers of the field's default country. Valid numbers are stored in the
    international format, so the cells, filters and sorting are the core text ones.
    Converting a field to this type keeps the existing values; only new values are
    checked.
    """

    type = "international_phone"
    model_class = InternationalPhoneField
    # No default value: a column default would skip the check.
    allowed_fields = ["phone_default_country"]
    serializer_field_names = list(allowed_fields)
    serializer_field_overrides = {
        "phone_default_country": serializers.ChoiceField(
            choices=["", *COUNTRIES],
            required=False,
            allow_blank=True,
            help_text="The country of numbers typed without + and a country code, "
            "like 'US'. If empty, every number must start with +.",
        ),
    }

    # The serializer's choices only cover API requests (see PatternTextFieldType).
    def before_create(
        self, table, primary, allowed_field_values, order, user, field_kwargs
    ):
        check_country(allowed_field_values.get("phone_default_country", ""))

    def before_update(self, from_field, to_field_values, user, field_kwargs):
        check_country(to_field_values.get("phone_default_country", ""))

    def get_compatible_filter_field_type(self, field):
        return field_type_registry.get(TextFieldType.type)

    def prepare_value_for_db(self, instance, value):
        return clean_phone(instance, value)

    def random_value(self, instance, fake, cache):
        return ""


class TelegramUsernameFieldType(NoTextDefaultMixin, TextFieldType):
    """
    A Telegram username, stored as "@name" so the cells, filters and sorting are
    the core text ones. Converting a field to this type cleans the values it holds
    the same way.
    """

    type = "telegram_username"
    model_class = TelegramUsernameField
    # No default value: a column default would skip the check.
    allowed_fields = []
    serializer_field_names = []

    def get_compatible_filter_field_type(self, field):
        return field_type_registry.get(TextFieldType.type)

    def prepare_value_for_db(self, instance, value):
        return clean_telegram_username(instance, value)

    # Converting a field to this type cleans the values it holds, like core's
    # email and URL fields (TextFieldMatchingRegexFieldType): "name" and t.me
    # links become "@name", and anything that isn't a username becomes ''.
    def get_alter_column_prepare_new_value(self, connection, from_field, to_field):
        if connection.vendor == "postgresql":
            return f"p_in = {TELEGRAM_CONVERT_SQL};"
        return super().get_alter_column_prepare_new_value(
            connection, from_field, to_field
        )

    def random_value(self, instance, fake, cache):
        return ""


def _check_time_format(time_format):
    if time_format not in dict(TIME_FORMAT_CHOICES):
        raise ValidationError(f"'{time_format}' isn't 24 or 12.", code="invalid")


class TimeOfDayFieldType(NoTextDefaultMixin, TextFieldType):
    """
    A time of day without a date, stored as 24 hour "HH:MM" text: it sorts in time
    order, and the cells and filters are the core text ones. Converting a field to
    this type cleans the values it holds the same way.
    """

    type = "time_of_day"
    model_class = TimeOfDayField
    # No default value: a column default would skip the check.
    allowed_fields = ["time_format"]
    serializer_field_names = list(allowed_fields)
    serializer_field_overrides = {
        "time_format": serializers.ChoiceField(
            choices=TIME_FORMAT_CHOICES,
            required=False,
            help_text="Show the time in the 24 hour (14:30) or 12 hour (2:30 PM) "
            "clock. Values are always stored as 24 hour HH:MM.",
        ),
    }

    # The serializer's choices only cover API requests (see PatternTextFieldType).
    def before_create(
        self, table, primary, allowed_field_values, order, user, field_kwargs
    ):
        _check_time_format(allowed_field_values.get("time_format", "24"))

    def before_update(self, from_field, to_field_values, user, field_kwargs):
        if "time_format" in to_field_values:
            _check_time_format(to_field_values["time_format"])

    def get_compatible_filter_field_type(self, field):
        return field_type_registry.get(TextFieldType.type)

    def prepare_value_for_db(self, instance, value):
        return clean_time(instance, value)

    # Converting a field to this type cleans the values it holds: times become
    # "HH:MM" and anything else becomes '', like TelegramUsernameFieldType.
    def get_alter_column_prepare_new_value(self, connection, from_field, to_field):
        if connection.vendor == "postgresql":
            return f"p_in = {TIME_CONVERT_SQL};"
        return super().get_alter_column_prepare_new_value(
            connection, from_field, to_field
        )

    def random_value(self, instance, fake, cache):
        return ""
