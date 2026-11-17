import { compile } from 'path-to-regexp'
import {
  ALLOWED_LINK_PROTOCOLS,
  PAGE_PARAM_TYPE_VALIDATION_FUNCTIONS,
} from '@baserow/modules/builder/enums'
import { BUILDER_PREVIEW_PATH_PREFIX } from '@baserow/modules/builder/utils/preview'
import { ensureString } from '@baserow/modules/core/utils/validator'
import { getUrlScheme } from '@baserow/modules/core/utils/url'

/**
 * Responsible for generating the data necessary to resolve an application builder
 * element URL. Used by LinkElement and LinkField to generate URLs, based on the
 * designer's navigation type / page / url choices.
 *
 * @param {Object} element The element's properties we'll use for generating the URL.
 * @param {Object} builder A builder application.
 * @param {Array} pages A list of pages of this application.
 * @param {Function} resolveFormula A resolveFormula function we'll use if the
 *  element has page parameters which need to be resolved.
 * @param {String} editorMode A builder application's editor mode.
 * @returns {String} A resolved URL.
 */
export default function resolveElementUrl(
  element,
  builder,
  pages,
  resolveFormula,
  editorMode
) {
  let resolvedUrl = ''
  if (element.navigation_type === 'page') {
    if (!isNaN(element.navigate_to_page_id)) {
      const page = pages.find(({ id }) => id === element.navigate_to_page_id)

      // The builder page list might be empty or the page has been deleted
      if (!page) {
        return resolvedUrl
      }

      const paramTypeMap = Object.fromEntries(
        page.path_params.map(({ name, type }) => [name, type])
      )

      const toPath = compile(page.path, { encode: encodeURIComponent })

      const pageParams = Object.fromEntries(
        element.page_parameters
          .filter(({ name }) => name in paramTypeMap)
          .map(({ name, value }) => [
            name,
            ensureString(
              PAGE_PARAM_TYPE_VALIDATION_FUNCTIONS[paramTypeMap[name]](
                resolveFormula(value)
              )
            ), // We ensure string here because toPath expect strings.
          ])
      )
      resolvedUrl = toPath(pageParams)
    }
  } else {
    resolvedUrl = ensureString(resolveFormula(element.navigate_to_url))
  }

  // Browsers strip leading C0 control characters and spaces before parsing
  // a URL, so ` javascript:` reads as relative here but still executes as
  // a script. Strip them before anything classifies this string.
  // eslint-disable-next-line no-control-regex
  resolvedUrl = resolvedUrl.replace(/^[\x00-\x20]+/, '')

  // Add query parameters if they exist
  if (element.query_parameters && element.query_parameters.length > 0) {
    const queryString = element.query_parameters
      .map(({ name, value }) => {
        if (!value) return null
        const resolvedValue = resolveFormula(value)
        if (!resolvedValue && String(resolvedValue) !== '0') return null
        return `${encodeURIComponent(name)}=${encodeURIComponent(
          resolvedValue
        )}`
      })
      .filter((param) => param !== null)
      .join('&')
    if (queryString) {
      const fragmentIndex = resolvedUrl.indexOf('#')
      const baseUrl =
        fragmentIndex === -1 ? resolvedUrl : resolvedUrl.slice(0, fragmentIndex)
      const fragment =
        fragmentIndex === -1 ? '' : resolvedUrl.slice(fragmentIndex)
      const separator = baseUrl.includes('?') ? '&' : '?'
      resolvedUrl = `${baseUrl}${separator}${queryString}${fragment}`
    }
  }
  // Browsers ignore tab / LF / CR anywhere in a URL,
  // so `java\tscript:` is still `javascript:`.
  const scheme = getUrlScheme(resolvedUrl)
  if (scheme) {
    // Disallow unsupported protocols, e.g. `javascript:`
    return ALLOWED_LINK_PROTOCOLS.includes(scheme) ? resolvedUrl : ''
  }
  return prefixInternalResolvedUrl(
    resolvedUrl,
    element.navigation_type,
    editorMode,
    builder.id,
    builder.base_path
  )
}

/**
 * Resolve a logical builder URL at the navigation boundary.
 *
 * @param {String} resolvedUrl A URL which `resolveElementUrl` has generated.
 * @param {String} navigationType An element's `navigation_type` (custom / page).
 * @param {String} editorMode A builder application's editor mode.
 * @param {Number} builderId The draft builder ID.
 * @param {String} basePath The path a published builder is served under, if any
 *  (see getPublishedLocation).
 * @returns {String} The resolved URL.
 */
export function prefixInternalResolvedUrl(
  resolvedUrl,
  navigationType,
  editorMode,
  builderId,
  basePath = ''
) {
  // Only internal URLs rendered in preview mode need the preview route.
  // Page navigation is always internal, while custom navigation is internal only
  // when it uses a root-relative URL.
  if (
    !resolvedUrl ||
    !(
      navigationType === 'page' ||
      (navigationType === 'custom' && resolvedUrl.startsWith('/'))
    )
  ) {
    return resolvedUrl
  }

  return resolveBuilderUrl(resolvedUrl, editorMode, builderId, basePath)
}

/**
 * Translate a logical builder page path into the URL for its rendering mode.
 * Published URLs stay unchanged, or go below their base path when the builder
 * is served under one; preview URLs live below the builder-scoped fixed route.
 */
export function resolveBuilderUrl(
  logicalPagePath,
  mode,
  builderId,
  basePath = ''
) {
  if (!logicalPagePath) {
    return logicalPagePath
  }
  if (mode !== 'preview') {
    // "//host/x" is protocol-relative, so another site.
    return basePath && !logicalPagePath.startsWith('//')
      ? prefixPath(logicalPagePath, basePath)
      : logicalPagePath
  }

  const previewPath = `${BUILDER_PREVIEW_PATH_PREFIX}/${builderId}`

  if (/^\/builder\/preview\/\d+(?:\/|\?|#|$)/.test(logicalPagePath)) {
    return logicalPagePath
  }

  if (logicalPagePath.startsWith('/?') || logicalPagePath.startsWith('/#')) {
    return `${previewPath}/${logicalPagePath.slice(1)}`
  }

  const path = logicalPagePath.startsWith('/')
    ? logicalPagePath
    : `/${logicalPagePath}`
  return `${previewPath}${path}`
}

/**
 * Puts a logical, root-relative path below `basePath` ("/app"). Callers pass
 * logical paths only, so a page path that starts like the base path ("/app/x")
 * is still prefixed.
 */
function prefixPath(path, basePath) {
  return `${basePath}${path.startsWith('/') ? '' : '/'}${path}`
}

/**
 * Where a published builder is served: on its own domain, or, for a route with
 * an `appSlug` param (the app_paths plugin), at /<appSlug> of a shared host
 * whose domain is stored as "<appSlug>.<host>".
 *
 * @param {Object} route The current route.
 * @param {String} hostname The request's hostname.
 * @returns {{domain: String, basePath: String}} The domain name to fetch the
 *  builder by, and the path its pages are below ('' for none).
 */
export function getPublishedLocation(route, hostname) {
  const slug = route.params?.appSlug
  if (slug === undefined) {
    return { domain: hostname, basePath: '' }
  }
  // Only a slug the app_paths backend allows (PathDomainType.SLUG): anything
  // else, like dots or decoded slashes, would reach the API path. `domain` is
  // then null and the site isn't found.
  return {
    domain: APP_SLUG.test(slug) ? `${slug}.${hostname}` : null,
    basePath: `/${slug}`,
  }
}

const APP_SLUG = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/
