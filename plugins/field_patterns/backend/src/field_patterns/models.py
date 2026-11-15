from django.db import models

from baserow.contrib.database.fields.models import TextField

PATTERN_MAX_LENGTH = 500

CASE_NONE = "none"
CASE_LOWER = "lower"
CASE_UPPER = "upper"
CASE_CHOICES = [(CASE_NONE, "None"), (CASE_LOWER, "Lower"), (CASE_UPPER, "Upper")]


class PatternTextField(TextField):
    """
    Single line text that must match `pattern`, after the value is cleaned up with
    `pattern_trim` and `pattern_case`. Empty values are allowed.
    """

    pattern = models.CharField(
        max_length=PATTERN_MAX_LENGTH,
        help_text="The regular expression the whole value must match.",
    )
    pattern_error_message = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Shown when a value doesn't match. A default is used if empty.",
    )
    pattern_trim = models.BooleanField(
        default=True, help_text="Remove spaces around the value before checking it."
    )
    pattern_case = models.CharField(
        max_length=8,
        choices=CASE_CHOICES,
        default=CASE_NONE,
        help_text="Change the value to lower or upper case before checking it.",
    )


class InternationalPhoneField(TextField):
    """
    A phone number of any country, stored in the international format, like
    "+44 20 7946 0958". Empty values are allowed.
    """

    phone_default_country = models.CharField(
        max_length=2,
        blank=True,
        default="",
        help_text="The country of numbers typed without + and a country code, like "
        "'US'. If empty, every number must start with +.",
    )


class TelegramUsernameField(TextField):
    """
    A Telegram username, stored as "@name". Empty values are allowed. Its own
    model only so the field type registry can tell it apart from text.
    """


TIME_FORMAT_24 = "24"
TIME_FORMAT_12 = "12"
TIME_FORMAT_CHOICES = [(TIME_FORMAT_24, "24 hour"), (TIME_FORMAT_12, "12 hour")]


class TimeOfDayField(TextField):
    """
    A time of day without a date, stored as 24 hour "HH:MM" text so it sorts in
    time order. `time_format` only decides how it's shown. Empty values are
    allowed.
    """

    time_format = models.CharField(
        max_length=2,
        choices=TIME_FORMAT_CHOICES,
        default=TIME_FORMAT_24,
        help_text="Show the time in the 24 hour (14:30) or 12 hour (2:30 PM) clock.",
    )
