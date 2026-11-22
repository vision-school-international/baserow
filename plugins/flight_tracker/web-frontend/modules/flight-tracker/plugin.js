import { defineNuxtPlugin } from '#imports'
import { FlightFieldType } from './fieldTypes'

export default defineNuxtPlugin({
  name: 'flight-tracker',
  // database/plugin.js registers the 'field' namespace.
  dependsOn: ['core', 'database'],
  setup(nuxtApp) {
    nuxtApp.$registry.register('field', new FlightFieldType({ app: nuxtApp }))
  },
})
