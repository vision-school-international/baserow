import { reactive } from 'vue'

/**
 * The flight statuses of the cells on screen, by `${fieldId}:${rowId}`. Cells ask
 * for theirs; the asks of one moment go out as one request per field
 * (flight_tracker/views.py FlightStatusView, at most 200 rows).
 */
const statuses = reactive({})
const askedAt = {}
const queue = new Map()
let timer = null
// The backend decides when AirLabs is asked again; this only spares requests.
const ASK_AGAIN_MS = 60 * 1000
const MAX_ROWS = 200

// flight.py ICAO / IATA: a bare number like 878 is no flight.
export const FLIGHT_REGEX = /^([A-Z]{3}|[A-Z][A-Z0-9]|[0-9][A-Z])\d{1,4}[A-Z]?$/

/** The cell's status, if it's for the flight the cell holds now. */
export function getStatus(fieldId, rowId, flight) {
  const status = statuses[`${fieldId}:${rowId}`]
  return status && flight && status.flight === flight ? status : null
}

async function flush(client) {
  timer = null
  const asks = [...queue]
  queue.clear()
  for (const [fieldId, rowIds] of asks) {
    const ids = [...rowIds]
    for (let i = 0; i < ids.length; i += MAX_ROWS) {
      const chunk = ids.slice(i, i + MAX_ROWS)
      try {
        const { data } = await client.get(
          `/database/fields/flight-tracker/${fieldId}/status/`,
          { params: { row_ids: chunk.join(',') } }
        )
        for (const [rowId, status] of Object.entries(data.statuses)) {
          statuses[`${fieldId}:${rowId}`] = status
        }
      } catch {
        // The cells show the flight number without a status.
      }
    }
  }
}

/**
 * Asks for the cell's status, unless it was asked for with the same flight a
 * moment ago: a cell edited to another flight asks again at once.
 */
export function askStatus(client, fieldId, rowId, flight, force = false) {
  const key = `${fieldId}:${rowId}:${flight}`
  if (!force && Date.now() - (askedAt[key] || 0) < ASK_AGAIN_MS) {
    return
  }
  askedAt[key] = Date.now()
  if (!queue.has(fieldId)) {
    queue.set(fieldId, new Set())
  }
  queue.get(fieldId).add(rowId)
  timer = timer || setTimeout(() => flush(client), 100)
}

/** "2021-07-21 18:50" (the airport's local time) -> "18:50". */
const timeOf = (value) => (value ? value.slice(11, 16) : '')

/** The text parts of a status, shared by the cell, card and row modal. */
export function describe(status, t) {
  if (!status) {
    return null
  }
  if (status.error) {
    return { state: t('flightTracker.notFound') }
  }
  // The latest known: actual, then estimated, then scheduled.
  const dep = timeOf(
    status.dep_actual || status.dep_estimated || status.dep_time
  )
  const arr = timeOf(
    status.arr_actual || status.arr_estimated || status.arr_time
  )
  const delay = Math.max(status.dep_delayed || 0, status.arr_delayed || 0)
  return {
    state: status.status
      ? t(`flightTracker.status.${status.status}`, status.status)
      : '',
    route: [
      [status.dep_iata, dep].filter(Boolean).join(' '),
      [status.arr_iata, arr].filter(Boolean).join(' '),
    ]
      .filter(Boolean)
      .join(' → '),
    delay: delay > 0 ? t('flightTracker.delay', { minutes: delay }) : '',
  }
}
