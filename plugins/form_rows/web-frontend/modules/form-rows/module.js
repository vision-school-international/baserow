import { addPlugin, createResolver, defineNuxtModule } from 'nuxt/kit'

// Same as telegram-share/module.js.
export default defineNuxtModule({
  meta: { name: 'form-rows' },
  setup(moduleOptions, nuxt) {
    const { resolve } = createResolver(import.meta.url)

    nuxt.options.css.push(resolve('./assets/scss/form-rows.scss'))

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
