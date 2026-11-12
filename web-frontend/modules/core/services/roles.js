export default (client, $registry) => {
  return {
    // TODO implement once endpoint exists
    get(workspace) {
      return {
        data: Object.values($registry.getAll('roles')).map((role) => ({
          uid: role.getUid(),
          icon: role.getIconClass(),
          description: role.getDescription(),
          invitationSubtitle: role.getInvitationSubtitle(workspace.id),
          isVisible: role.isVisible(workspace.id),
          isDefaultForInvitations: role.getIsDefaultForInvitations(
            workspace.id
          ),
          allowedScopeTypes: role.allowedScopeTypes,
          allowedSubjectTypes: role.allowedSubjectTypes,
        })),
      }
    },
  }
}
