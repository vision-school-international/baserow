import {
  ToolPresentationType,
  WORKSPACE_TOOL_GROUP,
} from '@baserow/modules/core/toolPresentationTypes'

/**
 * Names and describes the agent_tools plugin's tools, like the database tools'
 * presenters (agent/toolPresentationTypes.js). Reads join the workspace group.
 */
class AgentToolPresentationType extends ToolPresentationType {
  static getType() {
    return this.tool
  }

  get group() {
    return this.constructor.read ? WORKSPACE_TOOL_GROUP : null
  }

  get labelKey() {
    const name = this.constructor.tool
      .split('_')
      .map((part) => part[0].toUpperCase() + part.slice(1))
      .join('')
    return `agentTools.${name}`
  }

  getLabel(t) {
    return t(this.labelKey)
  }

  getDescription(t) {
    return t(`${this.labelKey}Description`)
  }
}

// [tool name, whether it only reads]; the same tools as the backend (tool_types.py).
const TOOLS = [
  ['list_applications', true],
  ['create_database', false],
  ['update_database', false],
  ['set_view_sorts', false],
  ['set_field_visibility', false],
  ['delete_view_filters', false],
  ['list_builders', true],
  ['create_builder', false],
  ['update_builder', false],
  ['list_pages', true],
  ['create_pages', false],
  ['update_page', false],
  ['setup_page', false],
  ['list_data_sources', true],
  ['create_data_sources', false],
  ['update_data_source', false],
  ['list_elements', true],
  ['create_display_elements', false],
  ['create_layout_elements', false],
  ['create_form_elements', false],
  ['create_collection_elements', false],
  ['update_element', false],
  ['update_element_style', false],
  ['move_elements', false],
  ['delete_element_items', false],
  ['list_element_actions', true],
  ['create_element_actions', false],
  ['add_element_action_field_mapping', false],
  ['update_element_action', false],
  ['set_theme', false],
  ['list_dashboards', true],
  ['create_dashboard', false],
  ['update_dashboard', false],
  ['list_widgets', true],
  ['get_widget_data', true],
  ['create_widgets', false],
  ['update_widgets', false],
  ['create_automation', false],
  ['update_automation', false],
  ['list_workflows', true],
  ['create_workflows', false],
  ['publish_workflow', false],
  ['pause_workflow', false],
  ['list_workflow_runs', true],
  ['list_nodes', true],
  ['add_nodes', false],
  ['update_nodes', false],
]

export const agentToolPresentationTypes = TOOLS.map(
  ([tool, read]) =>
    class extends AgentToolPresentationType {
      static tool = tool
      static read = read
    }
)
