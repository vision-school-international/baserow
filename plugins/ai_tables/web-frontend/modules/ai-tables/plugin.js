import { defineNuxtPlugin } from '#imports'
import { AIPromptTextFieldType, AIPromptChoiceFieldType } from './fieldTypes'
import {
  AIPromptFieldsFeatureType,
  AITablesPlugin,
  GenerateAIPromptValuesJobType,
  GenerateValuesContextItemType,
  TransformAICellsJobType,
  TransformCellsSelectionItemType,
} from './registerables'

export default defineNuxtPlugin({
  name: 'ai-tables',
  // database/plugin.js registers 'field', 'fieldContextItem' and
  // 'gridSelectionContextItem', core 'job' and 'aiProviderModelFeature'.
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
    $registry.register('job', new TransformAICellsJobType(context))
    $registry.register(
      'gridSelectionContextItem',
      new TransformCellsSelectionItemType(context)
    )
    $registry.register('plugin', new AITablesPlugin(context))
  },
})
