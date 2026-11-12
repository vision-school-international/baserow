import { defineNuxtPlugin } from '#imports'
import { AIPromptTextFieldType, AIPromptChoiceFieldType } from './fieldTypes'
import {
  AIPromptFieldsFeatureType,
  GenerateAIPromptValuesJobType,
  GenerateValuesContextItemType,
} from './registerables'

export default defineNuxtPlugin({
  name: 'ai-tables',
  // database/plugin.js registers 'field' and 'fieldContextItem', core 'job' and
  // 'aiProviderModelFeature'.
  dependsOn: ['core', 'database'],
  setup(nuxtApp) {
    const { $registry } = nuxtApp
    const context = { app: nuxtApp }

    $registry.register('field', new AIPromptTextFieldType(context))
    $registry.register('field', new AIPromptChoiceFieldType(context))
    $registry.register('job', new GenerateAIPromptValuesJobType(context))
    $registry.register(
      'aiProviderModelFeature',
      new AIPromptFieldsFeatureType(context)
    )
    $registry.register(
      'fieldContextItem',
      new GenerateValuesContextItemType(context)
    )
  },
})
