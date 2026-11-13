import { defineNuxtPlugin } from '#imports'
import { InterCPAuthProviderType } from './authProviderTypes'
import { WorkspaceMembersAdminType } from './adminTypes'

export default defineNuxtPlugin({
  name: 'intercp-auth',
  // core/plugin.js:169 registers the 'authProvider' namespace, :188 'admin'.
  dependsOn: ['core'],
  setup(nuxtApp) {
    nuxtApp.$registry.register(
      'authProvider',
      new InterCPAuthProviderType({ app: nuxtApp })
    )
    nuxtApp.$registry.register(
      'admin',
      new WorkspaceMembersAdminType({ app: nuxtApp })
    )
  },
})
