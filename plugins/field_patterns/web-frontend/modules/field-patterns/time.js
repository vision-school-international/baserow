// The browser side of field_patterns/times.py `clean_time`, kept to the same
// rules: "14:30", "9:05", "2:30 pm", "2pm", "12:00 a.m.", "14:30:00".
const TIME = /^(\d{1,2})(?::(\d{2})(?::00)?)?(?:\s*([ap])\.?m\.?)?$/i
const STORED = /^(\d{2}):(\d{2})$/

/**
 * The time as the backend stores it, 24 hour "HH:MM", or null if it isn't a
 * time of day. Empty values are returned as they are.
 */
export function parseTime(value) {
  if (value === null || value === undefined) {
    return value
  }
  const text = `${value}`.trim()
  if (text === '') {
    return ''
  }
  const match = TIME.exec(text)
  // A bare number like "14" is more likely a mistake than a time.
  if (!match || (match[2] === undefined && match[3] === undefined)) {
    return null
  }
  let hour = parseInt(match[1], 10)
  const minute = parseInt(match[2] ?? '0', 10)
  if (match[3]) {
    if (hour < 1 || hour > 12) {
      return null
    }
    hour = (hour % 12) + (match[3].toLowerCase() === 'p' ? 12 : 0)
  }
  if (hour > 23 || minute > 59) {
    return null
  }
  return `${`${hour}`.padStart(2, '0')}:${`${minute}`.padStart(2, '0')}`
}

/**
 * A stored "HH:MM" shown in the field's clock: "14:30" or "2:30 PM". Anything
 * else, like a value kept from before the field was converted, is shown as is.
 */
export function formatTime(value, timeFormat) {
  const match = STORED.exec(value ?? '')
  if (!match || timeFormat !== '12') {
    return value ?? ''
  }
  const hour = parseInt(match[1], 10)
  return `${hour % 12 || 12}:${match[2]} ${hour < 12 ? 'AM' : 'PM'}`
}
