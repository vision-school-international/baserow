import { defineNuxtPlugin } from '#imports'
import { FlightFieldType, FlightTrackerFieldType } from './fieldTypes'
import { FlightStatusViewFilterType } from './viewFilters'

export default defineNuxtPlugin({
  name: 'flight-tracker',
  // database/plugin.js registers the 'field' and 'viewFilter' namespaces.
  dependsOn: ['core', 'database'],
  setup(nuxtApp) {
    const { $registry } = nuxtApp
    $registry.register('field', new FlightFieldType({ app: nuxtApp }))
    $registry.register('field', new FlightTrackerFieldType({ app: nuxtApp }))
    $registry.register(
      'viewFilter',
      new FlightStatusViewFilterType({ app: nuxtApp })
    )
  },
})
