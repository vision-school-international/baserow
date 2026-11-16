import re

from django.core.exceptions import ValidationError

# a-z, 0-9 and underscores, 2 to 32 characters (owner's rule, 2026-11-16).
# core.telegram.org/method/account.updateUsername's 5-32 is only for choosing a
# basic username; collectible ones bought on Fragment are shorter.
USERNAME = re.compile(r"[A-Za-z0-9_]{2,32}")
# Digits only is a phone number, not a username (owner's rule, 2026-11-15).
DIGITS = re.compile(r"[0-9]+")
# A t.me link to the profile is read as its username.
LINK_PREFIX = re.compile(r"^(https?://)?(www\.)?(t|telegram)\.me/", re.IGNORECASE)

# The same rules in SQL, for the values a field converted to this type already
# holds (TelegramUsernameFieldType.get_alter_column_prepare_new_value). Like
# core's email and URL fields, a value that isn't one becomes ''.
CONVERT_SQL = r"""(select case when p_in is null then null
    when n ~ '^[A-Za-z0-9_]{2,32}$' and n !~ '^[0-9]+$' then '@' || n else '' end
  from (select regexp_replace(regexp_replace(regexp_replace(p_in::text,
    '^\s+|\s+$', '', 'g'), '^(https?://)?(www\.)?(t|telegram)\.me/', '', 'i'),
    '^@', '') as n) s)"""


def clean_telegram_username(field, value):
    """
    Returns the username as "@name", typed as "@name", "name" or a t.me link, or
    raises a ValidationError if it isn't one. Empty values are returned as they are.
    """

    if value is None or value == "":
        return value
    value = str(value).strip()
    if value == "":
        return value

    name = LINK_PREFIX.sub("", value).removeprefix("@")
    if not USERNAME.fullmatch(name) or DIGITS.fullmatch(name):
        raise ValidationError(
            "Enter a Telegram username: 2 to 32 letters, digits or underscores, "
            "not a phone number.",
            code="invalid",
        )
    return f"@{name}"
