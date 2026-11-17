import { describe, expect, test } from 'vitest'
import CustomCodeThemeConfigBlock from '../../../../plugins/custom_code/web-frontend/modules/custom-code/components/CustomCodeThemeConfigBlock.vue'

const { save, order, remove } = CustomCodeThemeConfigBlock.methods
const row = (key, values) => ({
  key,
  type: 'script',
  url: `https://a.test/${key}.js`,
  load: '',
  crossorigin: '',
  ...values,
})

describe('CustomCodeThemeConfigBlock asset rows', () => {
  test('saves only rows with a valid URL, without their keys', () => {
    const ctx = {
      values: {},
      rows: [
        row('a', { load: 'defer' }),
        row('b', { url: 'javascript:alert(1)' }),
        row('c', {
          url: 'https://a.test/c.css',
          type: 'stylesheet',
          load: 'async',
        }),
        row('d', { url: '' }),
      ],
    }
    save.call(ctx)
    expect(ctx.values.custom_assets).toEqual([
      {
        type: 'script',
        url: 'https://a.test/a.js',
        load: 'defer',
        crossorigin: '',
      },
      // A stylesheet is never deferred or async.
      {
        type: 'stylesheet',
        url: 'https://a.test/c.css',
        load: '',
        crossorigin: '',
      },
    ])
  })

  test('reorders and removes rows', () => {
    const ctx = { values: {}, rows: [row('a'), row('b'), row('c')] }
    order.call(ctx, ['c', 'a', 'b'])
    expect(ctx.rows.map((r) => r.key)).toEqual(['c', 'a', 'b'])
    remove.call(ctx, ctx.rows[1])
    expect(ctx.rows.map((r) => r.key)).toEqual(['c', 'b'])
  })
})

describe('CustomCodeThemeConfigBlock reset', () => {
  test('rebuilds the rows from the saved assets', async () => {
    const saved = [
      { type: 'script', url: 'https://a.test/s.js', load: '', crossorigin: '' },
    ]
    const ctx = {
      values: { custom_assets: [] },
      rows: [row('unsaved')],
      getDefaultValues: () => ({ custom_assets: saved }),
      $nextTick: () => Promise.resolve(),
      getChildForms: () => [],
    }
    await CustomCodeThemeConfigBlock.methods.reset.call(ctx)
    expect(ctx.rows.map(({ key, ...asset }) => asset)).toEqual(saved)
  })
})
