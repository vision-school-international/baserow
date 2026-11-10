import { toFormulaStringLiteral } from '@baserow/modules/core/formula'
import { TRIGGER_FIRED_AT_PATH } from '@baserow/modules/agent/dataProviderTypes'

/**
 * The opening message of a new trigger: its name and the time it fired, which
 * suits every trigger type. It is built the way the simple-mode editor emits
 * text followed by a data chip, so it opens as such.
 *
 * @param {Function} t The translate function.
 * @param {string} triggerName The display name of the trigger type.
 * @returns {object} The message formula object.
 */
export function defaultTriggerMessage(t, triggerName) {
  const firedAt = t('agent.triggerDefaultMessage', { trigger: triggerName })
  const text = toFormulaStringLiteral(`${firedAt} `)
  return {
    formula: `concat(${text}, get('trigger.${TRIGGER_FIRED_AT_PATH}'))`,
    mode: 'simple',
    version: '0.1',
  }
}
