import { defineNuxtPlugin } from '#imports'
import {
  GoogleSheetsDataSyncType,
  GoogleSheetsPushStrategyType,
} from './registerables'

export default defineNuxtPlugin({
  name: 'sheets-sync',
  // database/plugin.js:416-417 registers the 'dataSync' and
  // 'twoWaySyncStrategy' namespaces.
  dependsOn: ['core', 'database'],
  setup(nuxtApp) {
    const { $registry } = nuxtApp
    const context = { app: nuxtApp }

    $registry.register('dataSync', new GoogleSheetsDataSyncType(context))
    $registry.register(
      'twoWaySyncStrategy',
      new GoogleSheetsPushStrategyType(context)
    )
  },
})
