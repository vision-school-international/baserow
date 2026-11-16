import MarkdownIt from 'markdown-it'

// The CommonJS build exports the class on `default`, the ES build directly
// (same as core/utils/markdownToHtml.js).
const Markdown = MarkdownIt?.default || MarkdownIt
// 'commonmark' like the backend's MarkdownIt() (telegram_share/share_cards.py).
const md = new Markdown('commonmark')

/**
 * The text of a form description, which is markdown (FormViewDescription.vue).
 * Mirrors share_cards.py markdown_to_text.
 */
export function markdownToText(content) {
  const parts = []
  for (const token of md.parse(content || '', {})) {
    if (token.type !== 'inline') continue
    for (const child of token.children || []) {
      if (child.type === 'text' || child.type === 'code_inline') {
        parts.push(child.content)
      } else if (child.type === 'softbreak' || child.type === 'hardbreak') {
        parts.push(' ')
      }
    }
    parts.push(' ')
  }
  return parts.join('').split(/\s+/).filter(Boolean).join(' ')
}

/**
 * The Open Graph tags of a shared view or form, so a chat app shows its card:
 * the picture drawn by the telegram_share plugin (/api/share-cards/<slug>.png).
 */
export function shareCardMeta(config, { slug, path, title, description }) {
  const { publicBackendUrl, publicWebFrontendUrl, brandName } = config.public
  const meta = [
    { property: 'og:type', content: 'website' },
    { property: 'og:title', content: title },
    { property: 'og:url', content: `${publicWebFrontendUrl}${path}` },
    {
      property: 'og:image',
      content: `${publicBackendUrl}/api/share-cards/${slug}.png`,
    },
    { property: 'og:image:width', content: '1200' },
    { property: 'og:image:height', content: '630' },
    { name: 'twitter:card', content: 'summary_large_image' },
  ]
  // Set by the brand plugin.
  if (brandName) {
    meta.push({ property: 'og:site_name', content: brandName })
  }
  if (description) {
    meta.push(
      { property: 'og:description', content: description },
      { name: 'description', content: description }
    )
  }
  return meta
}
