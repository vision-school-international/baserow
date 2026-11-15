import re

from django.core.exceptions import ValidationError

# "14:30", "9:05", "2:30 pm", "2pm", "12:00 a.m.", and "14:30:00" from a Postgres
# time cast to text. Seconds are only accepted as :00: they aren't stored.
TIME = re.compile(
    r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2})(?::00)?)?"
    r"(?:\s*(?P<half>[ap])\.?m\.?)?",
    re.IGNORECASE,
)
INVALID = "Enter a time like 14:30 or 2:30 PM."


def clean_time(field, value):
    """
    Returns the time as 24 hour "HH:MM", or raises a ValidationError if it isn't
    a time of day. Empty values are returned as they are. Same shape as
    telegram.py's clean_telegram_username.
    """

    if value is None or value == "":
        return value
    value = str(value).strip()
    if value == "":
        return value

    match = TIME.fullmatch(value)
    # A bare number like "14" is more likely a mistake than a time.
    if match is None or (match["minute"] is None and match["half"] is None):
        raise ValidationError(INVALID, code="invalid")
    hour, minute = int(match["hour"]), int(match["minute"] or 0)
    if match["half"]:
        if not 1 <= hour <= 12:
            raise ValidationError(
                "With AM or PM, the hour must be 1 to 12.", code="invalid"
            )
        hour = hour % 12 + (12 if match["half"].lower() == "p" else 0)
    if hour > 23 or minute > 59:
        raise ValidationError(INVALID, code="invalid")
    return f"{hour:02d}:{minute:02d}"
