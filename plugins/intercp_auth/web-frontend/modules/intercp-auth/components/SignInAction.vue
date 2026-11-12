<template>
  <Button
    tag="a"
    :href="signInUrl"
    target="_self"
    type="primary"
    full-width
    size="large"
  >
    Sign in with {{ provider.name }}
  </Button>
</template>

<script>
import { isRelativeUrl } from '@baserow/modules/core/utils/url'

// shortcut: English-only copy, the plugin registers no locale files; add them if the
// instance ever needs another language.
export default {
  name: 'InterCPSignInAction',
  props: {
    // The login option the backend returned for this provider type.
    options: {
      type: Object,
      required: true,
    },
    original: {
      type: String,
      required: false,
      default: null,
    },
  },
  computed: {
    provider() {
      return this.options.items[0]
    },
    signInUrl() {
      const url = new URL(this.provider.redirect_url)
      if (this.original && isRelativeUrl(this.original)) {
        url.searchParams.set('original', this.original)
      }
      const { workspaceInvitationToken, invitationLinkSlug } = this.$route.query
      if (workspaceInvitationToken) {
        url.searchParams.set('workspace_invitation_token', workspaceInvitationToken)
      }
      if (invitationLinkSlug) {
        url.searchParams.set('workspace_invitation_link_slug', invitationLinkSlug)
      }
      return url.toString()
    },
  },
}
</script>
