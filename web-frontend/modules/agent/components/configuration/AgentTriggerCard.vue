<template>
  <article class="agent-trigger-card" :aria-busy="saving">
    <header class="agent-trigger-card__header">
      <div class="agent-trigger-card__type">
        <Icon
          :icon="serviceType?.icon || 'iconoir-flash'"
          class="agent-trigger-card__icon"
          aria-hidden="true"
        />
        <span class="agent-trigger-card__name">{{
          serviceType?.name || trigger.type
        }}</span>
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
        <i
          class="agent-trigger-card__chevron iconoir-nav-arrow-down"
          aria-hidden="true"
        />
      </div>
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
        :aria-describedby="serviceType ? summaryId : undefined"
        :aria-checked="trigger.enabled"
        :aria-disabled="!editable"
        :model-value="trigger.enabled"
        :disabled="!editable"
        @update:model-value="$emit('update', { enabled: $event })"
        @keydown.enter.prevent="toggleEnabled"
        @keydown.space.prevent="toggleEnabled"
      />
    </header>
    <div v-if="serviceType" class="agent-trigger-card__body">
      <div class="agent-trigger-card__service">
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
      </div>
      <p v-if="serviceError" class="agent-trigger-card__error" role="alert">
        {{ serviceError }}
      </p>
      <div class="agent-trigger-card__summary">
        <p :id="summaryId" class="agent-trigger-card__summary-text">
          {{ summary }}
        </p>
        <p v-if="skippedText" class="agent-trigger-card__skipped" role="status">
          {{ skippedText }}
        </p>
      </div>
      <div class="agent-trigger-card__overlap">
        <FormGroup :label="$t('agent.triggerOnOverlap')" small-label required>
          <Dropdown
            :model-value="trigger.on_overlap"
            :disabled="!editable"
            :show-search="false"
            fixed-items
            size="large"
            @update:model-value="$emit('update', { on_overlap: $event })"
          >
            <DropdownItem
              v-for="option in TRIGGER_OVERLAP_OPTIONS"
              :key="option.value"
              :value="option.value"
              :name="$t(option.label)"
            />
          </Dropdown>
        </FormGroup>
      </div>
      <FormGroup
        class="agent-trigger-card__message"
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
              {{ $t('agent.triggerDataProvides') }}
            </span>
            <span class="agent-trigger-card__schema-count">
              {{
                $t('agent.triggerDataValues', {
                  count: schemaProperties.length,
                })
              }}
            </span>
            <i
              class="agent-trigger-card__schema-chevron"
              :class="
                expanded ? 'iconoir-nav-arrow-down' : 'iconoir-nav-arrow-right'
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
        :aria-describedby="serviceType ? summaryId : undefined"
        @click="$emit('delete')"
      >
        {{ $t('agent.deleteTrigger') }}
      </ButtonText>
    </footer>
  </article>
</template>

<script setup>
import { computed, inject, provide, reactive, ref, toRef, useId } from 'vue'
import { useNuxtApp } from '#app'
import { useI18n } from 'vue-i18n'
import Icon from '@baserow/modules/core/components/Icon'
import ButtonText from '@baserow/modules/core/components/ButtonText'
import FormulaInputField from '@baserow/modules/core/components/formula/FormulaInputField'
import AgentTriggerMessageInput from '@baserow/modules/agent/components/configuration/AgentTriggerMessageInput'
import { serviceTypeOf } from '@baserow/modules/agent/utils/triggers'
import moment from '@baserow/modules/core/moment'
import {
  TRIGGER_OVERLAP_OPTIONS,
  TRIGGER_SKIP_REASON_TEXT,
} from '@baserow/modules/agent/constants'

const props = defineProps({
  /** The trigger as the card shows it, edits included. */
  trigger: { type: Object, required: true },
  /** The Agent's workspace, for the hosted service form. */
  workspace: { type: Object, default: null },
  /** Whether the user may change the trigger. */
  editable: Boolean,
  /** Whether a save of the trigger is in flight. */
  saving: Boolean,
  /** Why the server rejected the service values, or ''. */
  serviceError: { type: String, default: '' },
})
const emit = defineEmits(['update', 'delete'])
const { $registry } = useNuxtApp()
const { t } = useI18n()
const agent = inject('agentApplication')
const form = ref(null)
const summaryId = useId()
const serviceType = computed(() => serviceTypeOf($registry, props.trigger.type))
// Hosted service forms inject these like in Automation's node side panel.
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
const configurationError = computed(
  () =>
    serviceType.value?.getErrorMessage({
      service: props.trigger.service,
      workspace: props.workspace,
    }) || ''
)
const summary = computed(() =>
  [
    serviceType.value?.getSummary(props.trigger.service),
    t('agent.triggerRunStartsConversation'),
  ]
    .filter(Boolean)
    .join(' ')
)
/** Why the last firing started nothing, until a later firing is accepted. */
const skippedText = computed(() => {
  const {
    last_skipped_on: skippedOn,
    last_fired_on: firedOn,
    last_skipped_reason: reason,
  } = props.trigger
  const reasonText = TRIGGER_SKIP_REASON_TEXT[reason]
  if (
    !skippedOn ||
    !reasonText ||
    (firedOn && !moment(skippedOn).isAfter(firedOn))
  ) {
    return ''
  }
  const skipped = moment(skippedOn)
  const format = skipped.isSame(moment(), 'day') ? 'LT' : 'L LT'
  return t(reasonText, { time: skipped.format(format) })
})
const schemaProperties = computed(() => {
  const schema = $registry
    .get('agentDataProvider', 'trigger')
    .getDataSchema({ trigger: props.trigger })
  return Object.entries(schema?.properties || {}).map(([key, property]) => ({
    key,
    title: property.title || key,
    type: property.type,
  }))
})

function onServiceValuesChanged(values) {
  if (!props.editable) return
  if (form.value?.isFormValid && !form.value.isFormValid()) return
  emit('update', { service: values })
}

function toggleEnabled() {
  if (props.editable) emit('update', { enabled: !props.trigger.enabled })
}
</script>
