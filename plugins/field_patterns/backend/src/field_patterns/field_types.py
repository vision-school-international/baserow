from django.core.exceptions import ValidationError

from rest_framework import serializers

from baserow.contrib.database.fields.field_types import TextFieldType
from baserow.contrib.database.fields.registries import field_type_registry

from .models import CASE_CHOICES, PATTERN_MAX_LENGTH, PatternTextField
from .patterns import check_pattern, clean_value


def _check_required_pattern(pattern):
    # An empty pattern would turn down every value that isn't empty.
    if not pattern:
        raise ValidationError("A pattern is required.", code="required")
    check_pattern(pattern)


class PatternTextFieldType(TextFieldType):
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
