import { describe, expect, test } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import {
  getPublishedLocation,
  prefixInternalResolvedUrl,
  resolveBuilderUrl,
} from '@baserow/modules/builder/utils/urlResolution'
import {
  PathDomainType,
  splitDomainName,
} from '../../../../plugins/app_paths/web-frontend/modules/app-paths/domainTypes'

const page = { template: '<div />' }

describe('app paths routing', () => {
  // The published routes kept on the shared host: core's (builder/routes.js)
  // and the plugin's.
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { name: 'health', path: '/_health', component: page },
      {
        name: 'application-builder-page',
        path: '/:pathMatch(.*)*',
        component: page,
      },
      {
        name: 'application-builder-app-path',
        path: '/:appSlug/:pathMatch(.*)*',
        component: page,
      },
    ],
  })

  test.each([
    ['/ygmc', 'ygmc', []],
    ['/ygmc/', 'ygmc', []],
    ['/ygmc/a/b', 'ygmc', ['a', 'b']],
  ])('%s is the app path route', (path, appSlug, pathMatch) => {
    const route = router.resolve(path)
    expect(route.name).toBe('application-builder-app-path')
    expect(route.params.appSlug).toBe(appSlug)
    expect(route.params.pathMatch || []).toEqual(pathMatch)
  })

  test('the bare host stays on the core route', () => {
    expect(router.resolve('/').name).toBe('application-builder-page')
  })
})

describe('app paths URL resolution', () => {
  test('locates the app by its slug on the shared host', () => {
    expect(
      getPublishedLocation({ params: { appSlug: 'ygmc' } }, 'apps.test')
    ).toEqual({ domain: 'ygmc.apps.test', basePath: '/ygmc' })
    expect(getPublishedLocation({ params: {} }, 'site.test')).toEqual({
      domain: 'site.test',
      basePath: '',
    })
  })

  test.each([
    ['/', '/ygmc/'],
    ['/about', '/ygmc/about'],
    // A page whose own path starts like the slug is still prefixed.
    ['/ygmc/info', '/ygmc/ygmc/info'],
    ['/?a=1', '/ygmc/?a=1'],
  ])('puts %s below the base path', (path, expected) => {
    expect(resolveBuilderUrl(path, 'public', 1, '/ygmc')).toBe(expected)
  })

  test('leaves other URLs and modes as they were', () => {
    expect(resolveBuilderUrl('/about', 'public', 1)).toBe('/about')
    expect(resolveBuilderUrl('/about', 'preview', 7, '/ygmc')).toBe(
      '/builder/preview/7/about'
    )
    expect(
      prefixInternalResolvedUrl('https://x.test/a', 'custom', 'public', 1, '/y')
    ).toBe('https://x.test/a')
    expect(prefixInternalResolvedUrl('/a', 'custom', 'public', 1, '/y')).toBe(
      '/y/a'
    )
  })
})

describe('PathDomainType', () => {
  const type = new PathDomainType({
    app: {
      $config: {
        public: {
          appPathsHost: 'apps.test',
          publicWebFrontendUrl: 'https://baserow.test',
        },
      },
      $i18n: { t: (key) => key },
    },
  })
  const domain = { type: 'path', domain_name: 'ygmc.apps.test' }

  test('shows and links the site at its path', () => {
    expect(splitDomainName('ygmc.apps.test')).toEqual(['ygmc', 'apps.test'])
    expect(type.getDisplayName(domain)).toBe('apps.test/ygmc')
    expect(type.getPublicUrl(domain)).toBe('https://apps.test/ygmc')
    expect(type.options).toHaveLength(1)
  })
})

describe('app paths review fixes', () => {
  test.each(['a.b', '..', '../../api/settings?', 'YGMC', '-x'])(
    'does not look up the invalid slug %s',
    (appSlug) => {
      expect(
        getPublishedLocation({ params: { appSlug } }, 'apps.test')
      ).toEqual({ domain: null, basePath: `/${appSlug}` })
    }
  )

  test('keeps protocol-relative links external', () => {
    expect(resolveBuilderUrl('//cdn.test/x', 'public', 1, '/ygmc')).toBe(
      '//cdn.test/x'
    )
  })
})
