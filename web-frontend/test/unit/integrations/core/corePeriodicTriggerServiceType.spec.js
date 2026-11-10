import { describe, expect, test, vi } from 'vitest'
import { ServiceType } from '@baserow/modules/core/serviceTypes'
import { CorePeriodicTriggerServiceType } from '@baserow/modules/integrations/core/serviceTypes'
import coreLocale from '@baserow/locales/en.json'
import integrationsLocale from '@baserow/modules/integrations/locales/en.json'

const makeServiceType = async () => {
  const { createI18n } = await vi.importActual('vue-i18n')
  const i18n = createI18n({
    legacy: false,
    locale: 'en',
    messages: { en: { ...coreLocale, ...integrationsLocale } },
  })
  return new CorePeriodicTriggerServiceType({ app: { $i18n: i18n.global } })
}

const schedule = (values) => ({
  interval: 'DAY',
  minute: 0,
  hour: 9,
  day_of_week: 0,
  day_of_month: 1,
  timezone: 'Europe/Amsterdam',
  ...values,
})

describe('CorePeriodicTriggerServiceType', () => {
  test('summarises each interval in one sentence', async () => {
    const serviceType = await makeServiceType()
    const summaries = [
      { interval: 'MINUTE', minute: 1 },
      { interval: 'MINUTE', minute: 5 },
      { interval: 'HOUR', minute: 15 },
      {},
      { interval: 'WEEK', day_of_week: 2, hour: 18, minute: 30 },
      { interval: 'MONTH', day_of_month: 31, timezone: 'UTC' },
    ].map((values) => serviceType.getSummary(schedule(values)))

    expect(summaries).toEqual([
      'Every minute.',
      'Every 5 minutes.',
      'Every hour at minute 15.',
      'Every day at 09:00 (Europe/Amsterdam).',
      'Every Wednesday at 18:30 (Europe/Amsterdam).',
      'On day 31 of every month at 09:00 (UTC).',
    ])
  })

  test('has no summary before an interval is chosen', async () => {
    const serviceType = await makeServiceType()

    expect(serviceType.getSummary(schedule({ interval: null }))).toBe('')
    expect(serviceType.getSummary(null)).toBe('')
  })

  test('a service type has no summary unless it describes one', () => {
    expect(new ServiceType({ app: {} }).getSummary({})).toBe('')
  })
})
