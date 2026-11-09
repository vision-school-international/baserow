import { DataProviderType } from '@baserow/modules/core/dataProviderTypes'

/**
 * The payload a trigger service delivers when it fires, offered to the
 * trigger's opening-message formula as `trigger.<property>`. The schema comes
 * from the trigger's service type, so no trigger type is special-cased here.
 */
export class TriggerDataProviderType extends DataProviderType {
  static getType() {
    return 'trigger'
  }

  get name() {
    return this.app.$i18n.t('agent.triggerData')
  }

  getDataSchema(applicationContext) {
    const service = applicationContext?.trigger?.service
    if (!service?.type || !this.app.$registry.exists('service', service.type)) {
      return null
    }
    const schema = this.app.$registry
      .get('service', service.type)
      .getDataSchema(service)
    return schema ? { ...schema, title: this.name } : null
  }
}
