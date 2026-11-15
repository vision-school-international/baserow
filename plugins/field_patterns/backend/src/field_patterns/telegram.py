import re

from django.core.exceptions import ValidationError

# "Accepted characters: a-z (case-insensitive), 0-9 and underscores. Length: 5-32
# characters." (core.telegram.org/method/account.updateUsername)
USERNAME = re.compile(r"[A-Za-z0-9_]{5,32}")
# A t.me link to the profile is read as its username.
LINK_PREFIX = re.compile(r"^(https?://)?(www\.)?(t|telegram)\.me/", re.IGNORECASE)


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
    if not USERNAME.fullmatch(name):
        raise ValidationError(
            "Enter a Telegram username: 5 to 32 letters, digits or underscores.",
            code="invalid",
        )
    return f"@{name}"
