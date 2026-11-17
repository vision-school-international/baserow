import {
  addPlugin,
  createResolver,
  defineNuxtModule,
  extendPages,
  resolvePath,
} from 'nuxt/kit'

// Same as custom-code/module.js, plus the route of the apps below a path.
export default defineNuxtModule({
  meta: { name: 'app-paths' },
  async setup(moduleOptions, nuxt) {
    const { resolve } = createResolver(import.meta.url)

    // Set at runtime from BASEROW_APP_PATHS_HOST (web-frontend/env-remap.mjs).
    nuxt.options.runtimeConfig.public.appPathsHost ??= ''

    const publicPage = await resolvePath(
      '@baserow/modules/builder/pages/publicPage.vue'
    )
    extendPages((pages) => {
      pages.push({
        name: 'application-builder-app-path',
        // An app published at /<appSlug> of the shared host (app_paths backend
        // PathDomain). Kept only on that host (plugin.js).
        path: '/:appSlug/:pathMatch(.*)*',
        file: publicPage,
        meta: {
          publishedBuilderRoute: true,
          middleware: ['userSourceAuthProviderCallback'],
        },
      })
    })

    nuxt.hook('i18n:registerModule', (register) => {
      // Only English is shipped (AGENTS.md); other languages fall back to it.
      register({
        langDir: resolve('./locales'),
        locales: [{ code: 'en', name: 'English', file: 'en.json' }],
      })
    })

    addPlugin({ src: resolve('./plugin.js') })
  },
})
