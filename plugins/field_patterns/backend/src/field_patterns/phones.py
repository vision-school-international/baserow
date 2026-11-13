from django.core.exceptions import ValidationError

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

# The countries phonenumbers has rules for, as two-letter codes like "GB".
COUNTRIES = sorted(phonenumbers.SUPPORTED_REGIONS)


def check_country(country: str):
    """Raises a ValidationError if the country isn't empty or a supported code."""

    if country and country not in phonenumbers.SUPPORTED_REGIONS:
        raise ValidationError(f"'{country}' isn't a supported country.", code="invalid")


def clean_phone(field, value):
    """
    Returns the phone number in the international format, or raises a
    ValidationError if it isn't a valid number. Empty values are returned as they are.
    """

    if value is None or value == "":
        return value
    value = str(value).strip()
    if value == "":
        return value

    country = field.phone_default_country or None
    try:
        # Lenient: punctuation, spaces and an "ext." are understood
        # (phonenumbers.parse docs).
        number = phonenumbers.parse(value, country)
    except NumberParseException as exc:
        if (
            country is None
            and exc.error_type == NumberParseException.INVALID_COUNTRY_CODE
        ):
            raise ValidationError(
                "Start the number with + and the country code.", code="invalid"
            )
        number = None
    if number is None or not phonenumbers.is_valid_number(number):
        raise ValidationError("Enter a valid phone number.", code="invalid")
    return phonenumbers.format_number(number, PhoneNumberFormat.INTERNATIONAL)
