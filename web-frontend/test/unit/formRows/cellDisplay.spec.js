import { describe, expect, test } from 'vitest'
import { cellDisplay } from '../../../../plugins/form_rows/web-frontend/modules/form-rows/utils'

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
