from datetime import timedelta
from types import SimpleNamespace

from django.utils import timezone

import pytest
from agent_tools.runs import list_workflow_runs
from agent_tools.tool_types import AGENT_TOOL_TYPES
from asgiref.sync import async_to_sync
from pydantic_ai import ToolReturn

from baserow.contrib.agent.registries import agent_tool_type_registry
from baserow.contrib.automation.workflows.exceptions import (
    AutomationWorkflowDoesNotExist,
)
from baserow.core.models import Agent
from baserow.core.tools import ToolContext


def test_agent_tools_are_registered_with_buildable_schemas():
    for tool_class in AGENT_TOOL_TYPES:
        tool = agent_tool_type_registry.get(tool_class.type).get_tool(None)
        assert "ctx" not in tool.function_schema.json_schema.get("properties", {})


class _ModelRun:
    """The model run a tool streams its readable request to (agent/test_tools.py)."""

    def __init__(self):
        self.input = {}

    async def emit(self, event):
        self.input = event.input


def _call_as_agent(name, ctx, arguments):
    # Through get_tool, like a reply: the call acts as the Agent identity.
    tool = agent_tool_type_registry.get(name).get_tool(ctx)
    result = async_to_sync(tool.function)(
        _ModelRun(), **tool.function_schema.validator.validate_python(arguments)
    )
    assert isinstance(result, ToolReturn), result
    return result.return_value


@pytest.fixture
def agent_workspace(data_fixture):
    """An Agent identity of a workspace with an application, dashboard and workflow."""

    workspace = data_fixture.create_workspace()
    builder = data_fixture.create_builder_application(workspace=workspace)
    page = data_fixture.create_builder_page(builder=builder, name="Home")
    first = data_fixture.create_builder_heading_element(page=page, value="'One'")
    second = data_fixture.create_builder_heading_element(page=page, value="'Two'")
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    data_fixture.create_text_field(table=table, name="Name", primary=True)
    amount = data_fixture.create_number_field(table=table, name="Amount")
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)
    automation = data_fixture.create_automation_application(workspace=workspace)
    workflow = data_fixture.create_automation_workflow(automation=automation)
    # Publishing refuses a workflow with no action after its trigger
    # (automation/tools/workflows.py _raise_if_never_runs).
    data_fixture.create_local_baserow_create_row_action_node(workflow=workflow)
    identity = Agent.objects.create(workspace=workspace, name="Ops")
    return SimpleNamespace(
        ctx=ToolContext(user=identity, workspace=workspace),
        builder=builder,
        page=page,
        first=first,
        second=second,
        table=table,
        amount=amount,
        dashboard=dashboard,
        automation=automation,
        workflow=workflow,
    )


def _summary_widget(data):
    # The widget shape of dashboard/tools/test_widget_write_tools.py `_summary`.
    return {
        "type": "summary",
        "title": "Total",
        "table_id": data.table.id,
        "field_id": data.amount.id,
        "aggregation_type": "sum",
    }


TOOL_ARGUMENTS = {
    "list_builders": lambda d: {},
    "list_pages": lambda d: {"builder_id": d.builder.id},
    "create_pages": lambda d: {
        "builder_id": d.builder.id,
        "pages": [{"name": "Two", "path": "/two"}],
    },
    "update_page": lambda d: {"page_id": d.page.id, "page": {"name": "Start"}},
    "list_elements": lambda d: {"page_id": d.page.id},
    "create_display_elements": lambda d: {
        "page_id": d.page.id,
        "elements": [{"ref": "h", "type": "heading", "value": "Hi"}],
    },
    "update_element_style": lambda d: {
        "element_id": d.first.id,
        "style": {"padding": 1},
    },
    "move_elements": lambda d: {
        "moves": [{"element_id": d.second.id, "before_id": d.first.id}]
    },
    "list_dashboards": lambda d: {},
    "list_widgets": lambda d: {"dashboard_id": d.dashboard.id},
    "create_widgets": lambda d: {
        "dashboard_id": d.dashboard.id,
        "widgets": [_summary_widget(d)],
    },
    "list_workflows": lambda d: {"automation_id": d.automation.id},
    "publish_workflow": lambda d: {"workflow_id": d.workflow.id},
    "list_workflow_runs": lambda d: {"workflow_id": d.workflow.id},
}


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("name", TOOL_ARGUMENTS)
def test_every_tool_acts_as_the_agent_identity(agent_workspace, name):
    value = _call_as_agent(
        name, agent_workspace.ctx, TOOL_ARGUMENTS[name](agent_workspace)
    )

    assert not (
        isinstance(value, dict) and (value.get("error") or value.get("errors"))
    ), value


@pytest.mark.django_db(transaction=True)
def test_update_widgets_acts_as_the_agent_identity(agent_workspace):
    ctx = agent_workspace.ctx
    created = _call_as_agent(
        "create_widgets",
        ctx,
        {
            "dashboard_id": agent_workspace.dashboard.id,
            "widgets": [_summary_widget(agent_workspace)],
        },
    )

    value = _call_as_agent(
        "update_widgets",
        ctx,
        {"widgets": [{"widget_id": created["created"][0]["id"], "title": "Sum"}]},
    )

    assert not value.get("errors"), value
    assert value["updated"][0]["title"] == "Sum"


@pytest.mark.django_db
def test_list_workflow_runs_lists_newest_first(data_fixture):
    user = data_fixture.create_user()
    workflow = data_fixture.create_automation_workflow(user=user)
    now = timezone.now()
    old = data_fixture.create_automation_workflow_history(
        workflow=workflow, started_on=now - timedelta(hours=1), status="success"
    )
    new = data_fixture.create_automation_workflow_history(
        workflow=workflow, started_on=now, status="error", message="Boom"
    )
    ctx = ToolContext(user=user, workspace=workflow.automation.workspace)

    runs = list_workflow_runs(ctx, workflow.id)

    assert [run["id"] for run in runs] == [new.id, old.id]
    assert runs[0]["status"] == "error"
    assert runs[0]["message"] == "Boom"
    assert [run["id"] for run in list_workflow_runs(ctx, workflow.id, limit=1)] == [
        new.id
    ]


@pytest.mark.django_db
def test_list_workflow_runs_hides_other_workspaces(data_fixture):
    workflow = data_fixture.create_automation_workflow()
    other_user = data_fixture.create_user()
    other_workspace = data_fixture.create_workspace(user=other_user)
    ctx = ToolContext(user=other_user, workspace=other_workspace)

    with pytest.raises(AutomationWorkflowDoesNotExist):
        list_workflow_runs(ctx, workflow.id)
