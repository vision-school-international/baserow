from django.contrib.auth.models import AbstractUser


def get_user_type(user: object) -> str | None:
    if not isinstance(user, AbstractUser):
        return None
    profile = getattr(user, "profile", None)
    # Old cached profiles must fail closed instead of loading a new field in async auth.
    kind = profile.__dict__.get("user_type") if profile is not None else None
    return kind if kind in ("human", "identity") else None


def is_user(user: object) -> bool:
    """Return whether the stored User represents a human, regardless of status."""

    return get_user_type(user) == "human"


def is_identity(user: object) -> bool:
    """Return whether the stored User represents a nonhuman identity."""

    return get_user_type(user) == "identity"
