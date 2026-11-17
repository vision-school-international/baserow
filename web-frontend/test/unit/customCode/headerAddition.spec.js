import { describe, expect, test } from 'vitest'
import { CustomCodePlugin } from '../../../../plugins/custom_code/web-frontend/modules/custom-code/plugins'

const plugin = new CustomCodePlugin({ app: {} })
const builder = (theme, untrusted = false) => ({
  theme,
  untrusted_content: untrusted,
})
const decode = (url) => decodeURIComponent(url.split(',').slice(1).join(','))

describe('CustomCodePlugin.getBuilderApplicationHeaderAddition', () => {
  const code = { custom_css: 'h1 { color: red; }', custom_js: 'window.x = 1' }

  test('adds the CSS and the JS to the published site', () => {
    const { link, script } = plugin.getBuilderApplicationHeaderAddition({
      builder: builder(code),
      mode: 'public',
    })
    expect(link).toHaveLength(1)
    expect(decode(link[0].href)).toBe(code.custom_css)
    expect(link[0].href.startsWith('data:text/css;')).toBe(true)
    expect(script).toHaveLength(1)
    expect(decode(script[0].src)).toBe(code.custom_js)
  })

  test('adds only the CSS to the preview', () => {
    const { link, script } = plugin.getBuilderApplicationHeaderAddition({
      builder: builder(code),
      mode: 'preview',
    })
    expect(link).toHaveLength(1)
    expect(script).toHaveLength(0)
  })

  test('adds nothing for untrusted content or empty code', () => {
    expect(
      plugin.getBuilderApplicationHeaderAddition({
        builder: builder(code, true),
        mode: 'public',
      })
    ).toEqual({})
    expect(
      plugin.getBuilderApplicationHeaderAddition({
        builder: builder({ custom_css: '', custom_js: '' }),
        mode: 'public',
      })
    ).toEqual({ link: [], script: [] })
  })

  test('loads external assets before the custom code, scripts only when published', () => {
    const theme = {
      ...code,
      custom_assets: [
        {
          type: 'stylesheet',
          url: 'https://a.test/a.css',
          crossorigin: 'anonymous',
        },
        {
          type: 'script',
          url: 'https://a.test/a.js',
          load: 'async',
          crossorigin: '',
        },
      ],
    }
    const published = plugin.getBuilderApplicationHeaderAddition({
      builder: builder(theme),
      mode: 'public',
    })
    expect(published.link.map((l) => l.href)[0]).toBe('https://a.test/a.css')
    expect(published.link[0].crossorigin).toBe('anonymous')
    expect(published.link[1].href.startsWith('data:text/css;')).toBe(true)
    expect(published.script[0]).toMatchObject({
      src: 'https://a.test/a.js',
      async: true,
    })
    expect(published.script[0].crossorigin).toBeUndefined()
    expect(published.script[1].src.startsWith('data:text/javascript;')).toBe(
      true
    )

    const preview = plugin.getBuilderApplicationHeaderAddition({
      builder: builder(theme),
      mode: 'preview',
    })
    expect(preview.link).toHaveLength(2)
    expect(preview.script).toHaveLength(0)
  })

  test('keeps a closing style tag inside the URL', () => {
    const { link } = plugin.getBuilderApplicationHeaderAddition({
      builder: builder({ custom_css: '</style><script>alert(1)</script>' }),
      mode: 'preview',
    })
    expect(link[0].href).not.toContain('<')
  })
})
