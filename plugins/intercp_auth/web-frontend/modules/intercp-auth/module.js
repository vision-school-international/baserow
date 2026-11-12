import { addPlugin, createResolver, defineNuxtModule, extendPages } from 'nuxt/kit'

export default defineNuxtModule({
  meta: { name: 'intercp-auth' },
  setup() {
    const { resolve } = createResolver(import.meta.url)

    extendPages((pages) => {
      // Child of core's `login-pages` route, so it gets the login layout.
      const loginPages = pages.find((route) => route.name === 'login-pages')
      if (!loginPages) {
        throw new Error('intercp-auth: core route "login-pages" not found.')
      }
      loginPages.children.push({
        name: 'login-intercp-error',
        path: '/login/intercp-error',
        file: resolve('./pages/loginError.vue'),
      })
    })

    addPlugin({ src: resolve('./plugin.js') })
  },
})
