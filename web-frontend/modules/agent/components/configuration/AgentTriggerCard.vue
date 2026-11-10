<template>
  <article class="agent-trigger-card" :aria-busy="saving">
    <header class="agent-trigger-card__header">
      <Icon
        :icon="serviceType.icon"
        class="agent-trigger-card__icon"
        aria-hidden="true"
      />
      <span class="agent-trigger-card__title">
        <span class="agent-trigger-card__name">{{ serviceType.name }}</span>
        <Icon
          v-if="configurationError"
          v-tooltip="configurationError"
          class="agent-trigger-card__status"
          icon="iconoir-warning-circle"
          type="error"
          size="small"
          role="img"
          :aria-label="configurationError"
        />
      </span>
      <span
        v-if="saving"
        class="agent-trigger-card__saving"
        role="status"
        :aria-label="$t('agent.saving')"
      />
      <SwitchInput
        class="agent-trigger-card__switch"
        small
        role="switch"
        :tabindex="editable ? 0 : -1"
        :aria-label="$t('agent.triggerEnabled')"
        :aria-checked="trigger.enabled"
        :aria-disabled="!editable"
        :model-value="trigger.enabled"
        :disabled="!editable"
        @update:model-value="$emit('update', { enabled: $event })"
        @keydown.enter.prevent="toggleEnabled"
        @keydown.space.prevent="toggleEnabled"
      />
    </header>
    <div class="agent-trigger-card__body">
      <component
        :is="serviceType.formComponent"
        ref="form"
        :application="agent"
        :service="trigger.service"
        :service-type="serviceType"
        :default-values="trigger.service"
        :loading="saving"
        @values-changed="onServiceValuesChanged"
      />
      <p v-if="serviceError" class="agent-trigger-card__error" role="alert">
        {{ serviceError }}
      </p>
      <FormGroup
        class="margin-top-2"
        :label="$t('agent.triggerMessage')"
        :helper-text="$t('agent.triggerMessageHelper')"
        small-label
      >
        <AgentTriggerMessageInput
          :model-value="trigger.message"
          :disabled="!editable"
          :placeholder="$t('agent.triggerMessagePlaceholder')"
          @update:model-value="$emit('update', { message: $event })"
        />
      </FormGroup>
      <Expandable
        v-if="schemaProperties.length"
        class="agent-trigger-card__schema"
      >
        <template #header="{ expanded, toggle }">
          <button
            type="button"
            class="agent-trigger-card__schema-toggle"
            :aria-expanded="expanded"
            @click="toggle"
          >
            <span class="agent-trigger-card__schema-title">
              {{
                $t('agent.triggerDataProvides', {
                  count: schemaProperties.length,
                })
              }}
            </span>
            <i
              class="agent-trigger-card__schema-chevron"
              :class="
                expanded ? 'iconoir-nav-arrow-up' : 'iconoir-nav-arrow-down'
              "
              aria-hidden="true"
            ></i>
          </button>
        </template>
        <ul class="agent-trigger-card__schema-list">
          <li v-for="property in schemaProperties" :key="property.key">
            <span>{{ property.title }}</span>
            <span class="agent-trigger-card__schema-type">{{
              property.type
            }}</span>
          </li>
        </ul>
      </Expandable>
    </div>
    <footer v-if="editable" class="agent-trigger-card__footer">
      <ButtonText
        type="secondary"
        size="small"
        button-type="button"
        icon="iconoir-bin"
        class="agent-trigger-card__delete"
        @click="$emit('delete')"
      >
        {{ $t('agent.deleteTrigger') }}
      </ButtonText>
    </footer>
  </article>
</template>

<script setup>
import { computed, inject, provide, reactive, ref, toRef } from 'vue'
import { useNuxtApp } from '#app'
import Icon from '@baserow/modules/core/components/Icon'
import ButtonText from '@baserow/modules/core/components/ButtonText'
import FormulaInputField from '@baserow/modules/core/components/formula/FormulaInputField'
import AgentTriggerMessageInput from '@baserow/modules/agent/components/configuration/AgentTriggerMessageInput'

const props = defineProps({
  trigger: { type: Object, required: true },
  workspace: { type: Object, default: null },
  editable: Boolean,
  saving: Boolean,
  serviceError: { type: String, default: '' },
})
const emit = defineEmits(['update', 'delete'])
const { $registry } = useNuxtApp()
const agent = inject('agentApplication')
const form = ref(null)
const serviceType = computed(() => $registry.get('service', props.trigger.type))
// Trigger forms hold no formulas; the plain input satisfies the NodeSidePanel host contract.
provide('formulaComponent', FormulaInputField)
provide('dataProvidersAllowed', [])
provide('workspace', toRef(props, 'workspace'))
provide(
  'applicationContext',
  reactive({
    get agent() {
      return agent.value
    },
    get trigger() {
      return props.trigger
    },
  })
)
// Like an automation node: the header flags it, the form shows field errors once touched.
const configurationError = computed(
  () =>
    serviceType.value.getErrorMessage({
      service: props.trigger.service,
      workspace: props.workspace,
    }) || ''
)
const schemaProperties = computed(() => {
  const schema = serviceType.value.getDataSchema(props.trigger.service)
  return Object.entries(schema?.properties || {}).map(([key, property]) => ({
    key,
    title: property.title || key,
    type: property.type,
  }))
})

function onServiceValuesChanged(values) {
  if (form.value?.isFormValid && !form.value.isFormValid()) return
  emit('update', { service: values })
}

function toggleEnabled() {
  if (props.editable) emit('update', { enabled: !props.trigger.enabled })
}
</script>
