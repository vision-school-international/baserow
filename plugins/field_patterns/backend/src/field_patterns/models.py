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
