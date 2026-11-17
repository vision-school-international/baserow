import { DomainType } from '@baserow/modules/builder/domainTypes'
import SubDomainDetails from '@baserow/modules/builder/components/domain/SubDomainDetails'
import PathDomainForm from './components/PathDomainForm'

/**
 * An app published at https://<host>/<slug>, the host being BASEROW_APP_PATHS_HOST.
 * Its domain_name is "<slug>.<host>" (app_paths backend PathDomain).
 */
export class PathDomainType extends DomainType {
  static getType() {
    return 'path'
  }

  get host() {
    return getAppPathsHost(this.app.$config)
  }

  get name() {
    return this.app.$i18n.t('pathDomainType.name')
  }

  get options() {
    if (!this.host) {
      return []
    }
    return [
      {
        name: this.app.$i18n.t('pathDomainType.option', { host: this.host }),
        // `domain` is DomainForm's option key; the path keeps it apart from a
        // subdomain option of the same host.
        value: { type: this.getType(), domain: `${this.host}/` },
      },
    ]
  }

  get detailsComponent() {
    // Its text holds: nothing to set up per app.
    return SubDomainDetails
  }

  get formComponent() {
    return PathDomainForm
  }

  getDisplayName(domain) {
    const [slug, host] = splitDomainName(domain.domain_name)
    return `${host}/${slug}`
  }

  getPublicUrl(domain) {
    const [slug, host] = splitDomainName(domain.domain_name)
    const url = new URL(this.app.$config.public.publicWebFrontendUrl)
    return `${url.protocol}//${host}${url.port ? `:${url.port}` : ''}/${slug}`
  }
}

/** BASEROW_APP_PATHS_HOST, normalized like the backend's setting. */
export const getAppPathsHost = (config) =>
  (config.public.appPathsHost || '').trim().toLowerCase()

/** "<slug>.<host>" as [slug, host]. */
export const splitDomainName = (domainName) => {
  const dot = domainName.indexOf('.')
  return [domainName.slice(0, dot), domainName.slice(dot + 1)]
}
