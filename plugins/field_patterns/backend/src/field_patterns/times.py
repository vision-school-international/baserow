import re

from django.core.exceptions import ValidationError

# "14:30", "9:05", "2:30 pm", "2pm", "12:00 a.m.", and "14:30:00" from a Postgres
# time cast to text. Seconds are only accepted as :00: they aren't stored. ASCII
# digits only, like CONVERT_SQL and the browser's time.js.
TIME = re.compile(
    r"(?P<hour>[0-9]{1,2})(?::(?P<minute>[0-9]{2})(?::00)?)?"
    r"(?:\s*(?P<half>[ap])\.?m\.?)?",
    re.IGNORECASE,
)
INVALID = "Enter a time like 14:30 or 2:30 PM."

# The same rules in SQL, for the values a field converted to this type already
# holds (TimeOfDayFieldType.get_alter_column_prepare_new_value). Like core's
# email and URL fields, a value that isn't a time becomes ''. No "%": core runs
# it with params (db/schema.py _alter_field), so the driver would read it.
CONVERT_SQL = r"""(select case when p_in is null then null
    when m is null or (m[2] is null and m[3] is null) then ''
    when m[3] is not null and (m[1]::int < 1 or m[1]::int > 12) then ''
    else (select case when h > 23 or mi > 59 then ''
            else lpad(h::text, 2, '0') || ':' || lpad(mi::text, 2, '0') end
          from (select case when m[3] is null then m[1]::int
                  else mod(m[1]::int, 12) + case when lower(m[3]) = 'p' then 12 else 0 end
                end as h, coalesce(m[2], '0')::int as mi) t)
    end
  from (select regexp_match(regexp_replace(p_in::text, '^\s+|\s+$', '', 'g'),
    '^([0-9]{1,2})(?::([0-9]{2})(?::00)?)?(?:\s*([ap])\.?m\.?)?$', 'i') as m) s)"""


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
