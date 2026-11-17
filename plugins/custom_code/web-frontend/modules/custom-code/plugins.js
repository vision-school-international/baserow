import { BaserowPlugin } from '@baserow/modules/core/plugins'

/**
 * As a `data:` URL the code is never parsed as HTML, so CSS containing
 * `</style>` can't end its tag and add a script.
 */
const dataUrl = (mimeType, code) =>
  `data:${mimeType};charset=utf-8,${encodeURIComponent(code)}`

export class CustomCodePlugin extends BaserowPlugin {
  static getType() {
    return 'custom_code'
  }

  /**
   * Adds the external assets, then the application's CSS and JavaScript, after
   * everything else so they win over the theme. Scripts only run on the
   * published site: the preview is on the editor's own origin by default
   * (BUILDER_PREVIEW_URL), where a script would run with the signed-in editor's
   * session.
   */
  getBuilderApplicationHeaderAddition({ builder, mode }) {
    if (builder.untrusted_content) {
      return {}
    }

    const theme = builder.theme || {}
    const runScripts = mode === 'public'
    const link = []
    const script = []
    const stylesheet = (href, crossorigin = '') =>
      link.push({
        rel: 'stylesheet',
        href,
        crossorigin: crossorigin || undefined,
        tagPosition: 'bodyClose',
      })

    for (const asset of theme.custom_assets || []) {
      if (asset.type === 'stylesheet') {
        stylesheet(asset.url, asset.crossorigin)
      } else if (runScripts) {
        script.push({
          src: asset.url,
          defer: asset.load === 'defer' || undefined,
          async: asset.load === 'async' || undefined,
          crossorigin: asset.crossorigin || undefined,
          tagPosition: 'bodyClose',
        })
      }
    }
    if (theme.custom_css) {
      stylesheet(dataUrl('text/css', theme.custom_css))
    }
    if (theme.custom_js && runScripts) {
      script.push({
        src: dataUrl('text/javascript', theme.custom_js),
        defer: true,
        tagPosition: 'bodyClose',
      })
    }
    return { link, script }
  }
}
