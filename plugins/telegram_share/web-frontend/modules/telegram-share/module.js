import { addPlugin, createResolver, defineNuxtModule } from 'nuxt/kit'

// Same as field-patterns/module.js.
export default defineNuxtModule({
  meta: { name: 'telegram-share' },
  setup(moduleOptions, nuxt) {
    const { resolve } = createResolver(import.meta.url)

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
