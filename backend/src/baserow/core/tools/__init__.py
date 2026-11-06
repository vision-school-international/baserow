"""
Tools shared by the clients that act for a user: the MCP server, Kuma and the
Agent Builder.

A shared tool is a plain function. Its first argument is a ``ToolContext`` and
the others are annotated with ``typing.Annotated`` and ``pydantic.Field``, so
every client can build its input schema from the signature. The docstring
describes the tool to any client, and must not mention a client's own tools.
"""

from dataclasses import dataclass, field
from typing import Callable

from django.contrib.auth.models import User

from baserow.core.models import Workspace
from baserow.core.user.types import Identity


def _ignore_status(message: str) -> None:
    pass


@dataclass
class ToolContext:
    """Who a shared tool acts for, and where it reports its progress."""

    user: User | Identity
    workspace: Workspace
    update_status: Callable[[str], None] = field(default=_ignore_status)
    timezone: str | None = None
    """The timezone date values are in, UTC when None. Set by the caller so
    tools use the execution timezone for either a user or an identity."""
