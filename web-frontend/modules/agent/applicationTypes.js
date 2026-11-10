import { AGENT_APPLICATION_TYPE } from '@baserow/modules/agent/constants'
import { ApplicationType } from '@baserow/modules/core/applicationTypes'
import AgentApplicationContext from '@baserow/modules/agent/components/AgentApplicationContext'
import AgentApplicationForm from '@baserow/modules/agent/components/AgentApplicationForm'
import AgentApplicationSidebar from '@baserow/modules/agent/components/AgentApplicationSidebar'
import { FF_AGENT_BUILDER } from '@baserow/modules/core/plugins/featureFlags'

export class AgentApplicationType extends ApplicationType {
  static getType() {
    return AGENT_APPLICATION_TYPE
  }

  getIconClass() {
    return 'baserow-icon-agent'
  }

  getIconColor() {
    return 'purple'
  }

  getName() {
    return this.app.$i18n.t('applicationType.agent')
  }

  getNamePlural() {
    return this.app.$i18n.t('applicationType.agents')
  }

  getViewLabel() {
    return this.app.$i18n.t('applicationType.viewAgent')
  }

  getDescription() {
    return this.app.$i18n.t('applicationType.agentDesc')
  }

  supportsTrash() {
    return false
  }

  getApplicationContextComponent() {
    return AgentApplicationContext
  }

  getApplicationFormComponent() {
    return AgentApplicationForm
  }

  getSidebarComponent() {
    return AgentApplicationSidebar
  }

  getOrder() {
    return 100
  }

  canBeCreated() {
    return this.app.$featureFlagIsEnabled(FF_AGENT_BUILDER)
  }

  isVisible(application) {
    return this.app.$hasPermission(
      'application.read',
      application,
      application.workspace.id
    )
  }

  /**
   * A shared conversation, which has no owner, and a trigger need builders, as
   * trashing them did.
   *
   * @param {object} application The agent, as the trash structure lists it.
   * @param {object} trashEntry The trash entry.
   * @param {number} workspaceId The id of the workspace of the agent.
   * @returns {boolean} Whether the entry can be restored.
   */
  canRestoreTrashEntry(application, trashEntry, workspaceId) {
    const operations = {
      agent_conversation:
        trashEntry.trash_item_owner === null
          ? ['agent_application.restore_conversation', 'application.update']
          : ['agent_application.restore_conversation'],
      agent_trigger: ['application.update'],
    }[trashEntry.trash_item_type]
    return (operations || []).every((operation) =>
      this.app.$hasPermission(operation, application, workspaceId)
    )
  }

  async select(application) {
    // Workspace permissions load in the route; they aren't loaded yet from All workspaces.
    await this.app.$router.push({
      name: 'agent-application',
      params: { agentId: application.id },
    })
    return true
  }

  delete(application) {
    const { $store, $router } = this.app
    if ($store.getters['application/isSelected'](application)) {
      $router.push({
        name: 'workspace',
        params: { workspaceId: application.workspace.id },
      })
    }
  }
}
