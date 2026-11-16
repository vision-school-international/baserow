"""
Agent tools around the functions Baserow's MCP server already offers for
databases, applications, dashboards and automations (contrib/*/mcp/*/tools.py),
so their permission checks and actions are the same. `changes_data` follows each
MCP tool's `read_only`. Core's agent app (contrib/agent/tool_types.py) already
gives the table, field, row and view tools.

Left out: tools that trash (delete_views, delete_widgets, delete_nodes), because
trashing needs a User, not an Agent identity (core/trash/handler.py:101; core
marks its own delete_fields agent tool xfail "#6259" in agent test_tools.py).
"""

from baserow.contrib.agent.registries import AgentToolType
from baserow.contrib.automation.tools import automations, nodes, workflows
from baserow.contrib.builder.tools import (
    actions,
    applications,
    data_sources,
    elements,
    pages,
    themes,
)
from baserow.contrib.dashboard.tools import dashboards, widgets
from baserow.contrib.database.mcp.table.tools import list_database_applications
from baserow.contrib.database.tools import databases, view_config

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
    # Databases (the rest are core's agent tools). list_tables only reaches
    # databases through their tables, so this lists the empty ones too.
    _tool("list_applications", "database", list_database_applications, False),
    _tool("create_database", "database", databases.create_database, True),
    _tool("update_database", "database", databases.update_database, True),
    _tool("set_view_sorts", "database", view_config.set_view_sorts, True),
    _tool("set_field_visibility", "database", view_config.set_field_visibility, True),
    _tool("delete_view_filters", "database", view_config.delete_view_filters, True),
    # Applications (the application builder).
    _tool("list_builders", "builder", applications.list_builders, False),
    _tool("create_builder", "builder", applications.create_builder, True),
    _tool("update_builder", "builder", applications.update_builder, True),
    _tool("list_pages", "builder", pages.list_pages, False),
    _tool("create_pages", "builder", pages.create_pages, True),
    _tool("update_page", "builder", pages.update_page, True),
    _tool("setup_page", "builder", pages.setup_page, True),
    _tool("list_data_sources", "builder", data_sources.list_data_sources, False),
    _tool("create_data_sources", "builder", data_sources.create_data_sources, True),
    _tool("update_data_source", "builder", data_sources.update_data_source, True),
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
    _tool("delete_element_items", "builder", elements.delete_element_items, True),
    _tool("list_element_actions", "builder", actions.list_element_actions, False),
    _tool("create_element_actions", "builder", actions.create_element_actions, True),
    _tool(
        "add_element_action_field_mapping",
        "builder",
        actions.add_element_action_field_mapping,
        True,
    ),
    _tool("update_element_action", "builder", actions.update_element_action, True),
    _tool("set_theme", "builder", themes.set_theme, True),
    # Dashboards.
    _tool("list_dashboards", "dashboard", dashboards.list_dashboards, False),
    _tool("create_dashboard", "dashboard", dashboards.create_dashboard, True),
    _tool("update_dashboard", "dashboard", dashboards.update_dashboard, True),
    _tool("list_widgets", "dashboard", widgets.list_widgets, False),
    _tool("get_widget_data", "dashboard", widgets.get_widget_data, False),
    _tool("create_widgets", "dashboard", widgets.create_widgets, True),
    _tool("update_widgets", "dashboard", widgets.update_widgets, True),
    # Automations.
    _tool("create_automation", "automation", automations.create_automation, True),
    _tool("update_automation", "automation", automations.update_automation, True),
    _tool("list_workflows", "automation", workflows.list_workflows, False),
    _tool("create_workflows", "automation", workflows.create_workflows, True),
    _tool("publish_workflow", "automation", workflows.publish_workflow, True),
    _tool("pause_workflow", "automation", workflows.pause_workflow, True),
    _tool("list_workflow_runs", "automation", list_workflow_runs, False),
    _tool("list_nodes", "automation", nodes.list_nodes, False),
    _tool("add_nodes", "automation", nodes.add_nodes, True),
    _tool("update_nodes", "automation", nodes.update_nodes, True),
]
