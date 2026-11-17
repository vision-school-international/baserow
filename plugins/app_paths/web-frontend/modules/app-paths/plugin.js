import { defineNuxtPlugin, useRequestURL, useRouter } from '#imports'
import { getAppPathsHost, PathDomainType } from './domainTypes'

export const APP_PATH_ROUTE = 'application-builder-app-path'

export default defineNuxtPlugin({
  name: 'app-paths',
  // After core's router plugin, which keeps published routes off the editor.
  dependsOn: ['core', 'builder', 'router'],
  setup(nuxtApp) {
    nuxtApp.$registry.register('domain', new PathDomainType({ app: nuxtApp }))

    // Anywhere but the shared host, "/a/b" is a page of the domain's own app.
    const host = getAppPathsHost(nuxtApp.$config)
    const router = useRouter()
    if (
      router.hasRoute(APP_PATH_ROUTE) &&
      (!host || useRequestURL().hostname !== host)
    ) {
      router.removeRoute(APP_PATH_ROUTE)
    }
  },
})
