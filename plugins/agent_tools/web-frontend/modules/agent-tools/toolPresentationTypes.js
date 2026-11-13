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
  ['list_builders', true],
  ['list_pages', true],
  ['create_pages', false],
  ['update_page', false],
  ['list_elements', true],
  ['create_display_elements', false],
  ['create_layout_elements', false],
  ['create_form_elements', false],
  ['create_collection_elements', false],
  ['update_element', false],
  ['update_element_style', false],
  ['move_elements', false],
  ['list_dashboards', true],
  ['list_widgets', true],
  ['create_widgets', false],
  ['update_widgets', false],
  ['list_workflows', true],
  ['publish_workflow', false],
  ['list_workflow_runs', true],
]

export const agentToolPresentationTypes = TOOLS.map(
  ([tool, read]) =>
    class extends AgentToolPresentationType {
      static tool = tool
      static read = read
    }
)
