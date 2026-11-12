import { Registerable } from '@baserow/modules/core/registry'

class RoleType extends Registerable {
  getUid() {
    return null
  }

  getIconClass() {
    return 'iconoir-shield'
  }

  getName() {
    return null
  }

  getDescription() {
    return null
  }

  // Whether this role should be selected initially when inviting someone.
  getIsDefaultForInvitations(workspaceId) {
    return false
  }

  // Optional explanation shown below pending invitations with this role.
  getInvitationSubtitle(workspaceId) {
    return null
  }

  // Indicates whether the role should be visible in the list.
  isVisible(workspaceId) {
    return true
  }

  // `null` equals all scope types.
  get allowedScopeTypes() {
    return null
  }

  // `null` equals all scope types.
  get allowedSubjectTypes() {
    return null
  }
}

export class AdminRoleType extends RoleType {
  static getType() {
    return 'admin'
  }

  getUid() {
    return 'ADMIN'
  }

  getIconClass() {
    return 'iconoir-crown'
  }

  getName() {
    const { $i18n: i18n } = this.app
    return i18n.t('roles.admin.name')
  }

  getDescription() {
    const { $i18n: i18n } = this.app
    return i18n.t('roles.admin.description')
  }
}

export class MemberRoleType extends RoleType {
  getIsDefaultForInvitations(workspaceId) {
    // Subclasses representing different roles must opt into being the default.
    return this.type === MemberRoleType.getType()
  }

  static getType() {
    return 'member'
  }

  getUid() {
    return 'MEMBER'
  }

  getIconClass() {
    return 'baserow-icon-team'
  }

  getName() {
    const { $i18n: i18n } = this.app
    return i18n.t('permission.member')
  }

  getDescription() {
    const { $i18n: i18n } = this.app
    return i18n.t('permission.memberDescription')
  }
}
