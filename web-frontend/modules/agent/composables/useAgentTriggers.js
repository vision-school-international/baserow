import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useNuxtApp } from '#app'
import { useI18n } from 'vue-i18n'
import debounce from 'lodash/debounce'
import isEqual from 'lodash/isEqual'
import { notifyIf } from '@baserow/modules/core/utils/error'
import AgentTriggerService from '@baserow/modules/agent/services/agentTriggers'
import { API_ERROR_CODE } from '@baserow/modules/agent/constants'
import { defaultTriggerMessage } from '@baserow/modules/agent/utils/triggers'

const TYPED_SAVE_DELAY = 500

/** Page-local trigger list of one Agent, saved through the triggers API. */
export function useAgentTriggers(agent) {
  const { $client, $registry } = useNuxtApp()
  const { t } = useI18n()
  const service = AgentTriggerService($client)
  const triggers = ref([])
  const loading = ref(false)
  const loadError = ref(false)
  const savingIds = reactive(new Set())
  const serviceErrors = reactive({})
  // Typed edits are batched per trigger so two cards never cancel each other.
  const pendingSaves = new Map()
  const scheduledSaves = new Map()
  // The form keeps showing rejected values, so they ride along until saved.
  const rejectedServiceValues = new Map()
  let scope = 0

  const agentId = () => agent.value?.id
  const scopeIsCurrent = (currentScope) => scope === currentScope
  const findTrigger = (triggerId) =>
    triggers.value.find((trigger) => trigger.id === triggerId)

  async function fetchTriggers() {
    if (!agentId()) return
    const currentScope = scope
    loading.value = true
    loadError.value = false
    try {
      const { data } = await service.list(agentId())
      if (scopeIsCurrent(currentScope)) {
        triggers.value = data
        forgetRejectedServiceValues()
      }
    } catch {
      if (scopeIsCurrent(currentScope)) loadError.value = true
    } finally {
      if (scopeIsCurrent(currentScope)) loading.value = false
    }
  }

  async function createTrigger(type) {
    const currentScope = scope
    const serviceType = $registry.get('service', type)
    try {
      const { data } = await service.create(agentId(), {
        type,
        message: defaultTriggerMessage(t, serviceType.name),
        service: serviceType.getDefaultValues(null, {}),
      })
      if (scopeIsCurrent(currentScope)) triggers.value.push(data)
      return data
    } catch (error) {
      notifyIf(error, 'trigger')
      return null
    }
  }

  async function save(trigger, values) {
    const currentScope = scope
    savingIds.add(trigger.id)
    try {
      const { data } = await service.update(agentId(), trigger.id, values)
      if (!scopeIsCurrent(currentScope)) return
      if ('service' in values) {
        forgetSavedServiceValues(trigger.id, values.service)
        const rejected = rejectedServiceValues.get(trigger.id)
        if (!rejected) delete serviceErrors[trigger.id]
        // A reply must not undo service values still waiting on the debounce.
        if (!pendingSaves.get(trigger.id)?.service) {
          Object.assign(trigger, {
            service: { ...data.service, ...rejected },
            schema: data.schema,
          })
        }
      }
    } catch (error) {
      if (!scopeIsCurrent(currentScope)) return
      if (
        error.response?.data?.error ===
        API_ERROR_CODE.TRIGGER_SERVICE_MISCONFIGURED
      ) {
        if (values.service)
          rememberRejectedServiceValues(trigger, values.service)
        const detail = error.response.data.detail
        serviceErrors[trigger.id] =
          typeof detail === 'string' ? detail : t('agent.triggerMisconfigured')
        return
      }
      notifyIf(error, 'trigger')
      fetchTriggers()
    } finally {
      if (scopeIsCurrent(currentScope)) savingIds.delete(trigger.id)
    }
  }

  /**
   * Keeps the rejected service values the form still shows, to send them again.
   *
   * @param {object} trigger The trigger whose save was rejected.
   * @param {object} serviceValues The service values of the rejected save.
   */
  function rememberRejectedServiceValues(trigger, serviceValues) {
    const stillShown = Object.fromEntries(
      Object.entries(serviceValues).filter(
        ([field, value]) =>
          field !== 'type' && isEqual(value, trigger.service[field])
      )
    )
    const rejected = { ...rejectedServiceValues.get(trigger.id), ...stillShown }
    if (Object.keys(rejected).length) {
      rejectedServiceValues.set(trigger.id, rejected)
    }
  }

  /**
   * Drops the rejected service values that a successful save has now replaced.
   *
   * @param {number} triggerId The id of the saved trigger.
   * @param {object} savedServiceValues The service values the server accepted.
   */
  function forgetSavedServiceValues(triggerId, savedServiceValues) {
    const remaining = Object.fromEntries(
      Object.entries(rejectedServiceValues.get(triggerId) || {}).filter(
        ([field]) => !(field in savedServiceValues)
      )
    )
    if (Object.keys(remaining).length) {
      rejectedServiceValues.set(triggerId, remaining)
    } else {
      rejectedServiceValues.delete(triggerId)
    }
  }

  /** Drops every rejected service value, as the remounted forms show the server state. */
  function forgetRejectedServiceValues() {
    rejectedServiceValues.clear()
    for (const key of Object.keys(serviceErrors)) delete serviceErrors[key]
  }

  /** The given values that differ from the trigger, service values field by field. */
  function changedValues(trigger, values) {
    const changed = {}
    for (const [key, value] of Object.entries(values)) {
      if (key === 'service') {
        const serviceChanges = Object.fromEntries(
          Object.entries(value).filter(
            ([field, fieldValue]) =>
              !isEqual(fieldValue, trigger.service[field])
          )
        )
        if (Object.keys(serviceChanges).length) changed.service = serviceChanges
      } else if (!isEqual(value, trigger[key])) {
        changed[key] = value
      }
    }
    return changed
  }

  function flushScheduledSave(triggerId) {
    const batch = pendingSaves.get(triggerId)
    pendingSaves.delete(triggerId)
    const trigger = findTrigger(triggerId)
    if (trigger && batch) save(trigger, batch)
  }

  function scheduleSave(trigger, values) {
    const pending = pendingSaves.get(trigger.id) || {}
    pendingSaves.set(trigger.id, {
      ...pending,
      ...values,
      ...(values.service
        ? { service: { ...pending.service, ...values.service } }
        : {}),
    })
    if (!scheduledSaves.has(trigger.id)) {
      scheduledSaves.set(
        trigger.id,
        debounce(flushScheduledSave, TYPED_SAVE_DELAY)
      )
    }
    scheduledSaves.get(trigger.id)(trigger.id)
  }

  function updateTrigger(trigger, values) {
    const {
      service: serviceValues,
      message,
      ...immediate
    } = changedValues(trigger, values)
    Object.assign(trigger, immediate)
    if (message !== undefined) trigger.message = message
    if (serviceValues)
      trigger.service = { ...trigger.service, ...serviceValues }
    if (Object.keys(immediate).length) save(trigger, immediate)
    if (serviceValues || message !== undefined) {
      scheduleSave(trigger, {
        ...(serviceValues
          ? {
              service: {
                type: trigger.service.type,
                ...rejectedServiceValues.get(trigger.id),
                ...serviceValues,
              },
            }
          : {}),
        ...(message !== undefined ? { message } : {}),
      })
    }
  }

  async function deleteTrigger(trigger) {
    const currentScope = scope
    scheduledSaves.get(trigger.id)?.cancel()
    pendingSaves.delete(trigger.id)
    rejectedServiceValues.delete(trigger.id)
    const index = triggers.value.indexOf(trigger)
    if (index === -1) return
    triggers.value.splice(index, 1)
    try {
      await service.delete(agentId(), trigger.id)
    } catch (error) {
      if (scopeIsCurrent(currentScope)) {
        triggers.value.splice(index, 0, trigger)
        notifyIf(error, 'trigger')
      }
    }
  }

  function reset() {
    for (const scheduled of scheduledSaves.values()) scheduled.cancel()
    scheduledSaves.clear()
    pendingSaves.clear()
    forgetRejectedServiceValues()
    ++scope
    triggers.value = []
    loading.value = false
    loadError.value = false
    savingIds.clear()
  }

  onMounted(fetchTriggers)
  watch(
    () => agent.value?.id,
    () => {
      reset()
      fetchTriggers()
    }
  )
  // Leaving the section must not drop a batch still waiting on the debounce.
  onBeforeUnmount(() => {
    for (const scheduled of scheduledSaves.values()) scheduled.flush()
  })

  return {
    triggers,
    loading,
    loadError,
    savingIds,
    serviceErrors,
    fetchTriggers,
    createTrigger,
    updateTrigger,
    deleteTrigger,
  }
}
