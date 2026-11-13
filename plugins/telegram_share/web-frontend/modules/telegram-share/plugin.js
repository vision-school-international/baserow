import { defineNuxtPlugin } from '#imports'
import { TelegramSendWorkflowActionType } from './workflowActionTypes'

export default defineNuxtPlugin({
  name: 'telegram-share',
  // database/plugin.js registers the 'databaseWorkflowActionType' namespace.
  dependsOn: ['core', 'database'],
  setup(nuxtApp) {
    nuxtApp.$registry.register(
      'databaseWorkflowActionType',
      new TelegramSendWorkflowActionType({ app: nuxtApp })
    )
  },
})
