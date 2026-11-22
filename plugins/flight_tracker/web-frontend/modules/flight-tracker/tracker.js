/**
 * The flight tracker's cells: JSON written by the backend (flight_tracker/
 * tracker.py to_cell). Cells on screen ask the backend to fill them; the asks
 * of one moment go out as one request per field, and the filled cells arrive
 * as live row updates.
 */
const askedAt = {}
const queue = new Map()
let timer = null
// The backend decides when AirLabs is asked again (the field's interval); this
// only spares requests.
const ASK_AGAIN_MS = 60 * 1000
const MAX_ROWS = 200

async function flush(client) {
  timer = null
  const asks = [...queue]
  queue.clear()
  for (const [fieldId, rowIds] of asks) {
    const ids = [...rowIds]
    for (let i = 0; i < ids.length; i += MAX_ROWS) {
      try {
        await client.post(
          `/database/fields/flight-tracker/tracker/${fieldId}/refresh/`,
          null,
          { params: { row_ids: ids.slice(i, i + MAX_ROWS).join(',') } }
        )
      } catch {
        // The cells keep their last data.
      }
    }
  }
}

/** Asks the backend to fill the cell, unless it was asked a moment ago. */
export function askFill(client, fieldId, rowId) {
  const key = `${fieldId}:${rowId}`
  if (Date.now() - (askedAt[key] || 0) < ASK_AGAIN_MS) {
    return
  }
  askedAt[key] = Date.now()
  if (!queue.has(fieldId)) {
    queue.set(fieldId, new Set())
  }
  queue.get(fieldId).add(rowId)
  timer = timer || setTimeout(() => flush(client), 100)
}

/** "2026-11-21 18:25" (the airport's local time) -> "18:25". */
export const timeOf = (value) => (value ? value.slice(11, 16) : '')

/** The latest known time of one end: actual, else estimated, else scheduled. */
export const latest = (place) =>
  place?.actual || place?.estimated || place?.scheduled || null

/** The one line shown in cells and cards, like the backend's summary(). */
export function summary(cell, t) {
  if (!cell) {
    return ''
  }
  if (cell.error === 'not_found') {
    return `${cell.flight}: ${t('flightTracker.notFound')}`
  }
  if (cell.error === 'invalid_flight_number') {
    return `${cell.flight}: ${t('flightTracker.notAFlight')}`
  }
  const end = (place) =>
    [place?.airport_iata, timeOf(latest(place))].filter(Boolean).join(' ')
  const route = [end(cell.departure), end(cell.arrival)]
    .filter(Boolean)
    .join(' → ')
  const gate = cell.departure?.gate
    ? `${t('flightTracker.gate')} ${cell.departure.gate}`
    : ''
  const status = cell.status
    ? t(`flightTracker.status.${cell.status}`, cell.status)
    : ''
  return [cell.flight, status, route, gate].filter(Boolean).join(' · ')
}
