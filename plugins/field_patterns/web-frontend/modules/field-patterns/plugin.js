import { defineNuxtPlugin } from '#imports'
import { InternationalPhoneFieldType, PatternTextFieldType } from './fieldTypes'

export default defineNuxtPlugin({
  name: 'field-patterns',
  // database/plugin.js registers the 'field' namespace.
  dependsOn: ['core', 'database'],
  setup(nuxtApp) {
    const { $registry } = nuxtApp
    $registry.register('field', new PatternTextFieldType({ app: nuxtApp }))
    $registry.register(
      'field',
      new InternationalPhoneFieldType({ app: nuxtApp })
    )
  },
})
