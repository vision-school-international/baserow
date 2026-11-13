import { defineNuxtPlugin } from '#imports'
import { AIPromptTextFieldType, AIPromptChoiceFieldType } from './fieldTypes'
import {
  AIPromptFieldsFeatureType,
  AITablesPlugin,
  GenerateAIPromptValuesJobType,
  GenerateValuesContextItemType,
  TransformAICellsJobType,
} from './registerables'
import TransformCellsContextItem from './components/TransformCellsContextItem.vue'

// The backend's TRANSFORMABLE_FIELD_TYPES (job_types.py).
const TRANSFORMABLE_FIELD_TYPES = ['text', 'long_text']

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
    $registry.register('job', new TransformAICellsJobType(context))
    $registry.register('plugin', new AITablesPlugin(context))

    // shortcut: wraps the core text field type instances, because core has no
    // registry for cell-selection menu items (GridView.vue getMultiSelectContextItems);
    // replace with such a registry if core gets one.
    for (const type of TRANSFORMABLE_FIELD_TYPES) {
      const fieldType = $registry.get('field', type)
      const original = fieldType.getGridViewContextItemsOnCellsSelection
      fieldType.getGridViewContextItemsOnCellsSelection = function (field) {
        return [...original.call(this, field), TransformCellsContextItem]
      }
    }
  },
})
