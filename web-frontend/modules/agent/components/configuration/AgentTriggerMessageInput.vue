<template>
  <FormulaInputField
    :value="modelValue"
    :nodes-hierarchy="nodesHierarchy"
    :mode="mode"
    :disabled="disabled"
    :placeholder="placeholder"
    context-position="left"
    :validation-context="{ dataProviderRegistry: dataProviders }"
    @input="$emit('update:modelValue', $event)"
    @update:mode="mode = $event"
  />
</template>

<script setup>
import { computed, inject, ref } from 'vue'
import { useNuxtApp } from '#app'
import FormulaInputField from '@baserow/modules/core/components/formula/FormulaInputField'
import { buildFormulaFunctionNodes } from '@baserow/modules/core/formula'
import { getDataNodesFromDataProvider } from '@baserow/modules/core/utils/dataProviders'

defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: null },
  disabled: Boolean,
})
defineEmits(['update:modelValue'])
const app = useNuxtApp()
const applicationContext = inject('applicationContext')
// The backend stores the formula string alone, so the mode is display state.
const mode = ref('simple')
const dataProviders = computed(() => [
  app.$registry.get('agentDataProvider', 'trigger'),
])
const nodesHierarchy = computed(() => {
  const dataNodes = getDataNodesFromDataProvider(
    dataProviders.value,
    applicationContext
  )
  return [
    {
      name: app.$i18n.t('runtimeFormulaTypes.formulaTypeData'),
      type: 'data',
      icon: 'iconoir-database',
      nodes: dataNodes,
      empty: dataNodes.length === 0,
      emptyText: app.$i18n.t('runtimeFormulaTypes.formulaTypeDataEmpty'),
    },
    ...buildFormulaFunctionNodes(app),
  ]
})
</script>
