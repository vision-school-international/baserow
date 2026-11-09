"""
Tools shared by the clients that act for a user: the MCP server, Kuma and the
Agent Builder.

A shared tool is a plain function. Its first argument is a ``ToolContext`` and
the others are annotated with ``typing.Annotated`` and ``pydantic.Field``, so
every client can build its input schema from the signature. The docstring
describes the tool to any client, and must not mention a client's own tools.

Public tool entry points use ``tool_execution`` so permission caches live for
one invocation, even when the caller reuses a context. Internal helpers share
that invocation's caches and must not start another execution boundary.
"""

from copy import copy
from dataclasses import dataclass, field, replace
from functools import wraps
from typing import Callable, Concatenate, ParamSpec, TypeVar

from django.contrib.auth.models import User

from baserow.core.cache import local_cache
from baserow.core.models import Workspace
from baserow.core.permission_manager import WorkspaceMemberOnlyPermissionManagerType
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


ToolParams = ParamSpec("ToolParams")
ToolResult = TypeVar("ToolResult")


def tool_execution(
    function: Callable[Concatenate[ToolContext, ToolParams], ToolResult],
) -> Callable[Concatenate[ToolContext, ToolParams], ToolResult]:
    """Start a fresh permission cache lifetime for one public shared tool call."""

    @wraps(function)
    def wrapped(
        ctx: ToolContext, *args: ToolParams.args, **kwargs: ToolParams.kwargs
    ) -> ToolResult:
        # Callers can run tools concurrently with the same user and workspace.
        # Keep request metadata, but isolate each execution's mutable caches.
        ctx = replace(ctx, user=copy(ctx.user), workspace=copy(ctx.workspace))
        cache_key = WorkspaceMemberOnlyPermissionManagerType.actor_cache_key
        # Membership decisions are also stored on the actor, which can outlive
        # both a request and a tool invocation. Preserve the cached profile kind:
        # missing/unknown discriminators must continue to fail closed.
        ctx.user.__dict__.pop(cache_key, None)
        if hasattr(ctx.workspace, "_prefetched_objects_cache"):
            ctx.workspace._prefetched_objects_cache = {
                key: value
                for key, value in ctx.workspace._prefetched_objects_cache.items()
                if key != "workspaceuser_set"
            }
        with local_cache.context():
            return function(ctx, *args, **kwargs)

    return wrapped
