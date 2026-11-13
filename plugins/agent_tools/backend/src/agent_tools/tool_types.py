"""
Agent tools around the functions Baserow's MCP server already offers for
applications, dashboards and automations (contrib/*/mcp/*/tools.py), so their
permission checks and actions are the same. `changes_data` follows each MCP tool's
`read_only`.
"""

from baserow.contrib.agent.registries import AgentToolType
from baserow.contrib.automation.tools import workflows
from baserow.contrib.builder.tools import applications, elements, pages
from baserow.contrib.dashboard.tools import dashboards, widgets

from .runs import list_workflow_runs


def _tool(type_name, group, function, changes_data):
    return type(
        f"{type_name.title().replace('_', '')}AgentToolType",
        (AgentToolType,),
        {
            "type": type_name,
            "group": group,
            "function": function,
            "changes_data": changes_data,
        },
    )


AGENT_TOOL_TYPES = [
    # Applications (the application builder).
    _tool("list_builders", "builder", applications.list_builders, False),
    _tool("list_pages", "builder", pages.list_pages, False),
    _tool("create_pages", "builder", pages.create_pages, True),
    _tool("update_page", "builder", pages.update_page, True),
    _tool("list_elements", "builder", elements.list_elements, False),
    _tool("create_display_elements", "builder", elements.create_display_elements, True),
    _tool("create_layout_elements", "builder", elements.create_layout_elements, True),
    _tool("create_form_elements", "builder", elements.create_form_elements, True),
    _tool(
        "create_collection_elements",
        "builder",
        elements.create_collection_elements,
        True,
    ),
    _tool("update_element", "builder", elements.update_element, True),
    _tool("update_element_style", "builder", elements.update_element_style, True),
    _tool("move_elements", "builder", elements.move_elements, True),
    # Dashboards.
    _tool("list_dashboards", "dashboard", dashboards.list_dashboards, False),
    _tool("list_widgets", "dashboard", widgets.list_widgets, False),
    _tool("create_widgets", "dashboard", widgets.create_widgets, True),
    _tool("update_widgets", "dashboard", widgets.update_widgets, True),
    # No delete_widgets: trashing needs a User, not an Agent identity
    # (core/trash/handler.py:101, agent test_tools.py xfail "#6259").
    # Automations.
    _tool("list_workflows", "automation", workflows.list_workflows, False),
    _tool("publish_workflow", "automation", workflows.publish_workflow, True),
    _tool("list_workflow_runs", "automation", list_workflow_runs, False),
]
