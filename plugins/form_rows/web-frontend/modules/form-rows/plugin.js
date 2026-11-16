import { defineNuxtPlugin } from '#imports'
import { FormWithRowsModeType } from './formViewModeTypes'

export default defineNuxtPlugin({
  name: 'form-rows',
  // database/plugin.js registers the 'formViewMode' namespace.
  dependsOn: ['core', 'database'],
  setup(nuxtApp) {
    nuxtApp.$registry.register(
      'formViewMode',
      new FormWithRowsModeType({ app: nuxtApp })
    )
  },
})
