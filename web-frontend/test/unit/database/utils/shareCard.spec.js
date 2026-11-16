import {
  markdownToText,
  shareCardMeta,
} from '@baserow/modules/database/utils/shareCard'

const config = {
  public: {
    publicBackendUrl: 'https://api.example.com',
    publicWebFrontendUrl: 'https://example.com',
    brandName: 'Vision School',
  },
}

const content = (meta, key) =>
  meta.find((tag) => tag.property === key || tag.name === key)?.content

describe('shareCard', () => {
  test('markdownToText keeps only the text, like the backend', () => {
    expect(markdownToText('**Bring** a [friend](https://example.com).')).toBe(
      'Bring a friend.'
    )
    expect(markdownToText('# Hi\n\n- one\n- two  \nthree')).toBe(
      'Hi one two three'
    )
    expect(markdownToText(null)).toBe('')
  })

  test('shareCardMeta points at the card picture of the slug', () => {
    const meta = shareCardMeta(config, {
      slug: 'abc_D-1',
      path: '/form/abc_D-1',
      title: 'Event sign-up',
      description: 'Bring a friend.',
    })

    expect(content(meta, 'og:image')).toBe(
      'https://api.example.com/api/share-cards/abc_D-1.png'
    )
    expect(content(meta, 'og:url')).toBe('https://example.com/form/abc_D-1')
    expect(content(meta, 'og:title')).toBe('Event sign-up')
    expect(content(meta, 'og:site_name')).toBe('Vision School')
    expect(content(meta, 'og:description')).toBe('Bring a friend.')
    expect(content(meta, 'twitter:card')).toBe('summary_large_image')
  })

  test('shareCardMeta leaves out an empty description', () => {
    const meta = shareCardMeta(config, { slug: 's', path: '/p', title: 'Grid' })

    expect(content(meta, 'og:description')).toBeUndefined()
    expect(content(meta, 'description')).toBeUndefined()
  })
})
