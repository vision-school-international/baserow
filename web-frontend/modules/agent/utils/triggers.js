import { toFormulaStringLiteral } from '@baserow/modules/core/formula'

/**
 * The opening message of a new trigger: its name and the time it fired, which
 * suits every trigger type. Only advanced mode shows a function call; it is
 * built unspaced, as that editor re-emits it.
 *
 * @param {Function} t The translate function.
 * @param {string} triggerName The display name of the trigger type.
 * @returns {object} The message formula object.
 */
export function defaultTriggerMessage(t, triggerName) {
  const firedAt = t('agent.triggerDefaultMessage', { trigger: triggerName })
  return {
    formula: `concat(${toFormulaStringLiteral(`${firedAt} `)},now())`,
    mode: 'advanced',
    version: '0.1',
  }
}
