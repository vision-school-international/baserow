import { Registerable } from '@baserow/modules/core/registry'
import CustomDomainDetails from '@baserow/modules/builder/components/domain/CustomDomainDetails'
import CustomDomainForm from '@baserow/modules/builder/components/domain/CustomDomainForm'
import SubDomainForm from '@baserow/modules/builder/components/domain/SubDomainForm'
import SubDomainDetails from '@baserow/modules/builder/components/domain/SubDomainDetails'

export class DomainType extends Registerable {
  get name() {
    return null
  }

  get detailsComponent() {
    return null
  }

  get formComponent() {
    return null
  }

  get options() {
    return []
  }

  /** How the domain is shown in the editor. */
  getDisplayName(domain) {
    return domain.domain_name
  }

  /** The URL the domain's published site is visited at. */
  getPublicUrl(domain) {
    const url = new URL(this.app.$config.public.publicWebFrontendUrl)
    return `${url.protocol}//${domain.domain_name}${
      url.port ? `:${url.port}` : ''
    }`
  }
}

export class CustomDomainType extends DomainType {
  static getType() {
    return 'custom'
  }

  get name() {
    return this.app.$i18n.t('domainTypes.customName')
  }

  get detailsComponent() {
    return CustomDomainDetails
  }

  get formComponent() {
    return CustomDomainForm
  }

  get options() {
    return [
      {
        name: this.app.$i18n.t('domainTypes.customName'),
        value: {
          type: this.getType(),
          domain: 'custom',
        },
      },
    ]
  }
}

export class SubDomainType extends DomainType {
  static getType() {
    return 'sub_domain'
  }

  get name() {
    return this.app.$i18n.t('domainTypes.subDomainName')
  }

  get options() {
    const domains = this.app.$config.public.baserowBuilderDomains ?? []
    return domains.map((domain) => ({
      name: this.app.$i18n.t('domainTypes.subDomain', { domain }),
      value: {
        type: this.getType(),
        domain,
      },
    }))
  }

  get detailsComponent() {
    return SubDomainDetails
  }

  get formComponent() {
    return SubDomainForm
  }
}
