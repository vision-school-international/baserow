import { describe, expect, test } from 'vitest'
import {
  cellDisplay,
  visibleRows,
} from '../../../../plugins/form_rows/web-frontend/modules/form-rows/utils'

const fields = [
  { id: 1, type: 'date', name: 'Arrival Time' },
  { id: 2, type: 'text', name: 'Driver' },
  { id: 3, type: 'link_row', name: 'Passengers' },
]
const row = (id, date, driver, pax) => ({
  id,
  values: { field_1: date, field_2: driver, field_3: pax },
  cells: [
    // Shown text sorts wrong on purpose: the date must sort by its real time.
    { text: date ? `x${id}` : '' },
    { text: driver || '' },
    { text: pax ? `${pax} passengers` : '' },
  ],
})
const rows = [
  row(1, '2026-11-19T13:00:00Z', 'Charter Bus', 0),
  row(2, '2026-11-17T09:30:00Z', 'ruth kim', 12),
  row(3, null, 'Ohgilbert', 3),
  row(4, '2026-11-16T23:00:00Z', 'Ruth Kim', 2),
]
const ids = (shown) => shown.map((r) => r.id)

describe('visibleRows', () => {
  test('no search, no sort: the view order', () => {
    expect(ids(visibleRows(rows, fields, '', { index: null }))).toEqual([
      1, 2, 3, 4,
    ])
  })

  test('search matches shown text in any case', () => {
    expect(ids(visibleRows(rows, fields, ' RUTH ', { index: null }))).toEqual([
      2, 4,
    ])
  })

  test('dates sort by time, empty last both ways', () => {
    expect(
      ids(visibleRows(rows, fields, '', { index: 0, desc: false }))
    ).toEqual([4, 2, 1, 3])
    expect(
      ids(visibleRows(rows, fields, '', { index: 0, desc: true }))
    ).toEqual([1, 2, 4, 3])
  })

  test('times in the same second sort by microseconds', () => {
    const late = row(5, '2026-11-16T23:00:00.500000Z', 'A', 1)
    const early = row(6, '2026-11-16T23:00:00Z', 'B', 1)
    expect(
      ids(visibleRows([late, early], fields, '', { index: 0, desc: false }))
    ).toEqual([6, 5])
  })

  test('a sort on a column that is gone keeps the view order', () => {
    expect(
      ids(visibleRows(rows, fields, '', { index: 9, desc: false }))
    ).toEqual([1, 2, 3, 4])
  })

  test('link counts sort by number, not text (0 is lowest)', () => {
    expect(
      ids(visibleRows(rows, fields, '', { index: 2, desc: false }))
    ).toEqual([1, 4, 3, 2])
  })
})

const registry = {
  get: () => ({ toHumanReadableString: (field, value) => value || '' }),
}

describe('cellDisplay', () => {
  test('link fields show a count with the field name', () => {
    const field = { type: 'link_row', name: 'Passengers' }
    expect(cellDisplay(registry, field, 4)).toEqual({ text: '4 passengers' })
    expect(cellDisplay(registry, field, 0)).toEqual({ text: '' })
  })

  test('select fields show chips', () => {
    const option = { id: 1, value: 'Van', color: 'blue' }
    expect(cellDisplay(registry, { type: 'single_select' }, option)).toEqual({
      chips: [option],
    })
    expect(cellDisplay(registry, { type: 'single_select' }, null)).toEqual({
      chips: [],
    })
    expect(
      cellDisplay(registry, { type: 'multiple_select' }, [option])
    ).toEqual({ chips: [option] })
  })

  test('other fields use the field type text', () => {
    expect(cellDisplay(registry, { type: 'text' }, 'Ruth Kim')).toEqual({
      text: 'Ruth Kim',
    })
    expect(cellDisplay(registry, { type: 'number' }, null)).toEqual({
      text: '',
    })
  })
})
