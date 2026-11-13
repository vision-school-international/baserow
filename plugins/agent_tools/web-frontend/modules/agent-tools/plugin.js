import { defineNuxtPlugin } from '#imports'
import { agentToolPresentationTypes } from './toolPresentationTypes'

export default defineNuxtPlugin({
  name: 'agent-tools',
  // Registered like the agent module's own tool presenters (agent/plugin.js).
  dependsOn: ['core', 'agent'],
  setup(nuxtApp) {
    const context = { app: nuxtApp }
    for (const ToolPresentation of agentToolPresentationTypes) {
      nuxtApp.$registry.register(
        'toolPresentation',
        new ToolPresentation(context)
      )
    }
  },
})
