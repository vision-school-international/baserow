import { addPlugin, createResolver, defineNuxtModule } from 'nuxt/kit'

export default defineNuxtModule({
  meta: { name: 'brand' },
  setup(moduleOptions, nuxt) {
    const { resolve } = createResolver(import.meta.url)

    // Same env names as the backend; NUXT_PUBLIC_BRAND_* overrides at runtime.
    nuxt.options.runtimeConfig.public.brandName ||=
      process.env.BRAND_NAME || 'Baserow'
    nuxt.options.runtimeConfig.public.brandUrl ||=
      process.env.BRAND_URL || 'https://baserow.io'

    // Core serves /img/* from its static folder (core/module.js). Nitro keeps the
    // first file it sees for a path, so putting this folder first lets a dropped-in
    // logo or favicon replace core's, file by file.
    nuxt.hook('nitro:config', (nitroConfig) => {
      nitroConfig.publicAssets ||= []
      nitroConfig.publicAssets.unshift({ baseURL: '/', dir: resolve('public') })
    })

    addPlugin({ src: resolve('./plugin.js') })
  },
})
