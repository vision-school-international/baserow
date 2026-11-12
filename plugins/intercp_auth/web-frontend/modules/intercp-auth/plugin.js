import { defineNuxtPlugin } from '#imports'
import { InterCPAuthProviderType } from './authProviderTypes'

export default defineNuxtPlugin({
  name: 'intercp-auth',
  // core/plugin.js:169 registers the 'authProvider' namespace.
  dependsOn: ['core'],
  setup(nuxtApp) {
    nuxtApp.$registry.register(
      'authProvider',
      new InterCPAuthProviderType({ app: nuxtApp })
    )
  },
})
