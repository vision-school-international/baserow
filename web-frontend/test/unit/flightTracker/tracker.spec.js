import { describe, expect, test, vi } from 'vitest'
import {
  askFill,
  summary,
} from '../../../../plugins/flight_tracker/web-frontend/modules/flight-tracker/tracker'
import { FlightStatusViewFilterType } from '../../../../plugins/flight_tracker/web-frontend/modules/flight-tracker/viewFilters'
import { FlightTrackerFieldType } from '../../../../plugins/flight_tracker/web-frontend/modules/flight-tracker/fieldTypes'

const t = (key) => key
// The backend's to_cell for the real AA6 answer (test_tracker.py AA6).
const AA6 = {
  schema: 1,
  flight: 'AA6',
  error: null,
  status: 'landed',
  departure: {
    airport_iata: 'HNL',
    gate: 'C3',
    scheduled: '2026-11-21 18:32',
    scheduled_utc: '2026-11-22 04:32',
    estimated: '2026-11-21 18:22',
    actual: '2026-11-21 18:25',
  },
  arrival: {
    airport_iata: 'DFW',
    scheduled: '2026-11-22 06:00',
    actual: '2026-11-22 05:41',
  },
}

describe('flight tracker field', () => {
  test('summary matches the backend summary()', () => {
    expect(summary(AA6, t)).toBe(
      'AA6 · flightTracker.status.landed · HNL 18:25 → DFW 05:41 · flightTracker.gate C3'
    )
    expect(summary(null, t)).toBe('')
    expect(summary({ flight: 'XX1', error: 'not_found' }, t)).toBe(
      'XX1: flightTracker.notFound'
    )
  })

  test('cells on screen ask for a fill in one request per field', async () => {
    vi.useFakeTimers()
    const post = vi.fn().mockResolvedValue({})
    askFill({ post }, 3, 10)
    askFill({ post }, 3, 11)
    askFill({ post }, 3, 10)
    await vi.advanceTimersByTimeAsync(200)
    expect(post).toHaveBeenCalledTimes(1)
    expect(post.mock.calls[0][0]).toBe(
      '/database/fields/flight-tracker/tracker/3/refresh/'
    )
    expect(post.mock.calls[0][2].params.row_ids).toBe('10,11')
    // Asked a moment ago: no new request.
    askFill({ post }, 3, 10)
    await vi.advanceTimersByTimeAsync(200)
    expect(post).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })

  test('the status filter matches like the backend filter', () => {
    const filter = Object.create(FlightStatusViewFilterType.prototype)
    expect(filter.matches(AA6, 'landed')).toBe(true)
    expect(filter.matches(AA6, 'en-route')).toBe(false)
    expect(filter.matches({ error: 'not_found' }, 'not_found')).toBe(true)
    expect(filter.matches(null, 'none')).toBe(true)
    expect(filter.matches(AA6, 'none')).toBe(false)
    expect(filter.matches(AA6, '')).toBe(true)
  })

  test('sorts by scheduled departure, empty first', () => {
    const type = Object.create(FlightTrackerFieldType.prototype)
    const later = { ...AA6, departure: { scheduled_utc: '2026-11-23 01:00' } }
    const rows = [{ f: later }, { f: null }, { f: AA6 }]
    rows.sort(type.getSort('f', 'ASC'))
    expect(rows.map((r) => r.f)).toEqual([null, AA6, later])
  })
})

describe('flight tracker components', () => {
  test('the row modal lists the flight details', async () => {
    const { mount } = await import('@vue/test-utils')
    const { default: RowEdit } =
      await import('../../../../plugins/flight_tracker/web-frontend/modules/flight-tracker/components/RowEditFieldFlightTracker.vue')
    // Imported for compiling only.
    await import('../../../../plugins/flight_tracker/web-frontend/modules/flight-tracker/components/FieldFlightTrackerSubForm.vue')
    const wrapper = mount(RowEdit, {
      props: {
        workspaceId: 1,
        field: { id: 2, flight_code_field_id: 1 },
        value: AA6,
        row: null,
        readOnly: true,
      },
      global: { mocks: { $t: (key) => key, $client: {}, $store: null } },
    })
    const text = wrapper.text()
    expect(text).toContain('HNL')
    expect(text).toContain('flightTracker.gate C3')
    expect(text).toContain('2026-11-21 18:32 → 2026-11-21 18:25')
    wrapper.unmount()
  })
})
