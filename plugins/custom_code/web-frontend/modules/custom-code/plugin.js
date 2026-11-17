import { defineNuxtPlugin } from '#imports'
import { CustomCodePlugin } from './plugins'
import { CustomCodeThemeConfigBlockType } from './themeConfigBlockTypes'

export default defineNuxtPlugin({
  name: 'custom-code',
  // builder/plugin.js registers the 'themeConfigBlock' namespace.
  dependsOn: ['core', 'builder'],
  setup(nuxtApp) {
    nuxtApp.$registry.register(
      'themeConfigBlock',
      new CustomCodeThemeConfigBlockType({ app: nuxtApp })
    )
    nuxtApp.$registry.register('plugin', new CustomCodePlugin({ app: nuxtApp }))
  },
})
