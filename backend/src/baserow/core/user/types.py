"""Identity annotations describe nonhuman users stored in Django's User model.

This alias does not distinguish the two kinds at runtime; use ``is_identity``
when behavior depends on whether the stored user is an identity.
"""

from typing import TypeAlias

from django.contrib.auth.models import User

Identity: TypeAlias = User
