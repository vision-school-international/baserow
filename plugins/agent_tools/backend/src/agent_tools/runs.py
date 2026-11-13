from typing import Annotated, Any

from pydantic import Field

from baserow.contrib.automation.history.handler import AutomationHistoryHandler
from baserow.contrib.automation.tools.workflows import get_workflow_in_workspace
from baserow.core.tools import ToolContext


def _iso(value):
    return value.isoformat() if value is not None else None


def list_workflow_runs(
    ctx: ToolContext,
    workflow_id: Annotated[
        int, Field(description="The ID of the workflow, from list_workflows.")
    ],
    limit: Annotated[
        int, Field(ge=1, le=50, description="How many of the latest runs to list.")
    ] = 10,
) -> list[dict[str, Any]]:
    """
    List the latest runs of a workflow, newest first: id, status (success, error,
    disabled, started, skipped or cancelled), started_on, completed_on, message,
    whether it was a test run, and who started it (empty when an event did).
    """

    # Checks the workflow is in the workspace and the user may read it.
    workflow = get_workflow_in_workspace(ctx, workflow_id)
    histories = AutomationHistoryHandler().get_workflow_histories(workflow)
    return [
        {
            "id": history.id,
            "status": history.status,
            "started_on": _iso(history.started_on),
            "completed_on": _iso(history.completed_on),
            "message": history.message,
            "is_test_run": history.is_test_run,
            "triggered_by": history.triggered_by_name,
        }
        # The model orders by -started_on (history/models.py).
        for history in histories[:limit]
    ]
