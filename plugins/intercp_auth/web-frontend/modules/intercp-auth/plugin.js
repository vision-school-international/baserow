import { defineNuxtPlugin } from '#imports'
import { InterCPAuthProviderType } from './authProviderTypes'

export default defineNuxtPlugin({
  name: 'intercp-auth',
  dependsOn: ['registry'],
  setup(nuxtApp) {
    nuxtApp.$registry.register(
      'authProvider',
      new InterCPAuthProviderType({ app: nuxtApp })
    )
  },
})
