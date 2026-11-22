import { describe, expect, test, vi } from 'vitest'
import {
  FLIGHT_REGEX,
  askStatus,
  describe as describeStatus,
  getStatus,
} from '../../../../plugins/flight_tracker/web-frontend/modules/flight-tracker/status'

const t = (key, arg) =>
  typeof arg === 'object' ? `${key}:${JSON.stringify(arg)}` : key

describe('flight tracker', () => {
  test('flight numbers match the backend (flight.py ICAO/IATA)', () => {
    for (const ok of [
      'AA6',
      'AAL6',
      'U21234',
      'BA2490A',
      'F9123',
      '9W1',
      'WN878',
    ]) {
      expect(FLIGHT_REGEX.test(ok)).toBe(true)
    }
    for (const bad of [
      '878',
      '1234',
      'A6',
      'AA',
      'AA12345',
      'AAAA6',
      'AA-6',
      'aa6',
    ]) {
      expect(FLIGHT_REGEX.test(bad)).toBe(false)
    }
  })

  test('asks for the statuses of a moment in one request per field', async () => {
    vi.useFakeTimers()
    const get = vi.fn().mockResolvedValue({
      data: { statuses: { 1: { flight: 'AA6', status: 'landed' } } },
    })
    const client = { get }
    askStatus(client, 7, 1, 'AA6')
    askStatus(client, 7, 2, 'BA1')
    askStatus(client, 7, 1, 'AA6')
    await vi.runAllTimersAsync()
    expect(get).toHaveBeenCalledTimes(1)
    expect(get.mock.calls[0][1].params.row_ids).toBe('1,2')
    expect(getStatus(7, 1, 'AA6').status).toBe('landed')
    // A status of another flight than the cell holds isn't shown.
    expect(getStatus(7, 1, 'BA1')).toBe(null)

    // Asked a moment ago: no new request, unless forced (the cell changed).
    askStatus(client, 7, 1, 'AA6')
    await vi.runAllTimersAsync()
    expect(get).toHaveBeenCalledTimes(1)
    askStatus(client, 7, 1, 'AA6', true)
    await vi.runAllTimersAsync()
    expect(get).toHaveBeenCalledTimes(2)
    // The cell now holds another flight: asked at once.
    askStatus(client, 7, 1, 'BA1')
    await vi.runAllTimersAsync()
    expect(get).toHaveBeenCalledTimes(3)
    vi.useRealTimers()
  })

  test('describes a status', () => {
    expect(describeStatus(null, t)).toBe(null)
    expect(describeStatus({ error: 'not_found' }, t).state).toBe(
      'flightTracker.notFound'
    )
    const text = describeStatus(
      {
        status: 'en-route',
        dep_iata: 'OGG',
        dep_time: '2021-07-21 18:50',
        arr_iata: 'DFW',
        arr_time: '2021-07-22 07:04',
        arr_estimated: '2021-07-22 07:20',
        arr_delayed: 16,
      },
      t
    )
    expect(text.state).toBe('flightTracker.status.en-route')
    expect(text.route).toBe('OGG 18:50 → DFW 07:20')
    expect(text.delay).toBe('flightTracker.delay:{"minutes":16}')
    // The actual time wins over the estimate (a real AirLabs answer has both).
    expect(
      describeStatus(
        {
          arr_iata: 'DFW',
          arr_time: '2026-11-22 06:00',
          arr_estimated: '2026-11-22 05:50',
          arr_actual: '2026-11-22 05:41',
        },
        t
      ).route
    ).toBe('DFW 05:41')
    // Free plan: no times or airports.
    expect(describeStatus({ status: 'scheduled' }, t).route).toBe('')
  })
})

describe('flight cells', () => {
  test('the grid cell shows the flight and its status', async () => {
    const { mount, flushPromises } = await import('@vue/test-utils')
    const { default: Cell } =
      await import('../../../../plugins/flight_tracker/web-frontend/modules/flight-tracker/components/FunctionalGridViewFieldFlight.vue')
    vi.useFakeTimers()
    const get = vi.fn().mockResolvedValue({
      data: {
        statuses: {
          5: {
            flight: 'AA6',
            status: 'landed',
            dep_iata: 'OGG',
            arr_iata: 'DFW',
          },
        },
      },
    })
    const wrapper = mount(Cell, {
      props: { value: 'AA6', field: { id: 9 }, row: { id: 5 } },
      global: {
        mocks: {
          $client: { get },
          $t: (key) => key,
          $store: { getters: { 'auth/isAuthenticated': true } },
        },
      },
    })
    // Not runAll: the cell's refresh interval never ends.
    await vi.advanceTimersByTimeAsync(200)
    await flushPromises()
    expect(get.mock.calls[0][0]).toBe(
      '/database/fields/flight-tracker/9/status/'
    )
    expect(wrapper.text()).toBe('AA6 flightTracker.status.landed · OGG → DFW')
    wrapper.unmount()
    vi.useRealTimers()
  })
})
