import { AdminType } from '@baserow/modules/core/adminTypes'

// Next to core's Users and Workspaces admin types (core/adminTypes.js).
export class WorkspaceMembersAdminType extends AdminType {
  static getType() {
    return 'intercp_workspace_members'
  }

  getIconClass() {
    return 'iconoir-add-user'
  }

  getName() {
    return this.$t('intercpWorkspaceMembers.title')
  }

  getCategory() {
    return this.$t('sidebar.people')
  }

  getRouteName() {
    return 'admin-intercp-workspace-members'
  }

  getOrder() {
    // Right after Workspaces (3).
    return 3.5
  }
}
