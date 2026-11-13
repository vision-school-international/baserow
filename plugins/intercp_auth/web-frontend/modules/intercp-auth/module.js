import { addPlugin, createResolver, defineNuxtModule, extendPages } from 'nuxt/kit'

export default defineNuxtModule({
  meta: { name: 'intercp-auth' },
  setup(moduleOptions, nuxt) {
    const { resolve } = createResolver(import.meta.url)

    nuxt.options.css.push(resolve('./assets/scss/telegram-sign-in.scss'))

    extendPages((pages) => {
      // Child of core's `login-pages` route, so it gets the login layout.
      const loginPages = pages.find((route) => route.name === 'login-pages')
      if (!loginPages) {
        throw new Error('intercp-auth: core route "login-pages" not found.')
      }
      // Login only: core's sign-up page is replaced by a redirect to the login page.
      const signup = loginPages.children.find((route) => route.name === 'signup')
      if (!signup) {
        throw new Error('intercp-auth: core route "signup" not found.')
      }
      signup.file = resolve('./pages/signupRedirect.vue')

      loginPages.children.push({
        name: 'login-intercp-error',
        path: '/login/intercp-error',
        file: resolve('./pages/loginError.vue'),
      })

      // Core's admin pages are children of `root` (core/routes.js:70-74).
      const root = pages.find((route) => route.name === 'root')
      if (!root) {
        throw new Error('intercp-auth: core route "root" not found.')
      }
      root.children.push({
        name: 'admin-intercp-workspace-members',
        path: '/admin/workspace-members',
        file: resolve('./pages/adminWorkspaceMembers.vue'),
      })
    })

    // Same registration as the ai-tables module; only English is shipped.
    nuxt.hook('i18n:registerModule', (register) => {
      register({
        langDir: resolve('./locales'),
        locales: [{ code: 'en', name: 'English', file: 'en.json' }],
      })
    })

    addPlugin({ src: resolve('./plugin.js') })
  },
})
