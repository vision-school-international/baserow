from functools import lru_cache

from django.core.exceptions import ValidationError

import regex

from .models import CASE_LOWER, CASE_UPPER

# Seconds one value may take to match, so a pattern like (a|aa)+ can't hang a worker.
MATCH_TIMEOUT = 0.1


@lru_cache(maxsize=256)
def _compile(pattern: str):
    # The `regex` library, like core's UnicodeRegexValidator, for unicode \w.
    return regex.compile(pattern)


def check_pattern(pattern: str):
    """Raises a ValidationError if the pattern isn't a valid regular expression."""

    try:
        _compile(pattern)
    except regex.error as exc:
        raise ValidationError(
            f"The pattern isn't a valid regular expression: {exc}", code="invalid"
        )


def clean_value(field, value):
    """
    Returns the value cleaned up as the field says, or raises a ValidationError if
    it doesn't match the field's pattern. Empty values are returned as they are.
    """

    if value is None or value == "":
        return value
    value = str(value)
    if field.pattern_trim:
        value = value.strip()
    if field.pattern_case == CASE_LOWER:
        value = value.lower()
    elif field.pattern_case == CASE_UPPER:
        value = value.upper()
    if value == "":
        return value

    check_pattern(field.pattern)
    try:
        matches = _compile(field.pattern).fullmatch(value, timeout=MATCH_TIMEOUT)
    except TimeoutError:
        raise ValidationError(
            "The value took too long to check against the pattern.", code="invalid"
        )
    if not matches:
        raise ValidationError(
            field.pattern_error_message or "The value doesn't match the pattern.",
            code="invalid",
        )
    return value
