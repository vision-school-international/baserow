import { AdminType } from '@baserow/modules/core/adminTypes'

// Next to core's Users and Workspaces admin types (core/adminTypes.js).
export class WorkspaceMembersAdminType extends AdminType {
  static getType() {
    return 'intercp_workspace_members'
  }

  getIconClass() {
    return 'iconoir-add-user'
  }

  // Registerables only have `this.app` (core/registry.js:10-11), so translate
  // through it like core's admin types (core/adminTypes.js:129-137).
  getName() {
    const { $i18n: i18n } = this.app
    return i18n.t('intercpWorkspaceMembers.title')
  }

  getCategory() {
    const { $i18n: i18n } = this.app
    return i18n.t('sidebar.people')
  }

  getRouteName() {
    return 'admin-intercp-workspace-members'
  }

  getOrder() {
    // Right after Workspaces (3).
    return 3.5
  }
}
