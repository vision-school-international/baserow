import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { reactive, ref } from 'vue'
import { TestApp } from '@baserow/test/helpers/testApp'
import { clone } from '@baserow/modules/core/utils/object'
import moment from '@baserow/modules/core/moment'
import FormulaInputField from '@baserow/modules/core/components/formula/FormulaInputField'
import AgentWhenItRunsSection from '@baserow/modules/agent/components/configuration/AgentWhenItRunsSection'
import AgentTriggerMessageInput from '@baserow/modules/agent/components/configuration/AgentTriggerMessageInput'
import AgentTriggerPicker from '@baserow/modules/agent/components/configuration/AgentTriggerPicker'
import { defaultTriggerMessage } from '@baserow/modules/agent/utils/triggers'
import agentLocale from '@baserow/modules/agent/locales/en.json'
import integrationsLocale from '@baserow/modules/integrations/locales/en.json'
import {
  agentData,
  choose,
  completeConfiguration,
  useFakeTimers,
  workspace,
} from './helpers'

const schema = {
  type: 'object',
  properties: {
    triggered_at: { type: 'string', title: 'Previous scheduled run' },
    next_run_at: { type: 'string', title: 'Next scheduled run' },
  },
}

const periodicTrigger = (extra = {}) => ({
  id: 1,
  type: 'periodic',
  enabled: true,
  message: { formula: "'Periodic trigger'", mode: 'simple', version: '0.1' },
  service: {
    id: 5,
    type: 'periodic',
    interval: 'HOUR',
    minute: 0,
    hour: 0,
    day_of_week: 0,
    day_of_month: 1,
    timezone: 'UTC',
    schema,
  },
  schema,
  ...extra,
})

const patches = (testApp) =>
  testApp.mock.history.patch.map(({ url, data }) => [url, JSON.parse(data)])

describe('Agent triggers', () => {
  let testApp, agent

  beforeEach(async () => {
    testApp = new TestApp()
    await testApp.store.dispatch('workspace/forceCreate', clone(workspace))
    agent = await testApp.store.dispatch(
      'application/forceCreate',
      clone(agentData)
    )
  })

  afterEach(async () => {
    await testApp.afterEach()
    vi.useRealTimers()
  })

  const mountSection = (triggers, availableTypes = ['periodic']) => {
    testApp.mock.onGet('/agent/10/triggers/').reply(200, triggers)
    return testApp.mount(AgentWhenItRunsSection, {
      props: {
        configuration: completeConfiguration({
          available_trigger_types: availableTypes,
        }),
        editable: true,
      },
      global: { provide: { agentApplication: ref(agent) } },
    })
  }

  test('hosts the trigger type form on the card and saves service values after the debounce', async () => {
    useFakeTimers()
    testApp.mock.onPatch('/agent/10/triggers/1/').reply((config) => {
      const saved = periodicTrigger()
      const body = JSON.parse(config.data)
      return [200, { ...saved, service: { ...saved.service, ...body.service } }]
    })
    const wrapper = await mountSection([periodicTrigger()])
    const card = wrapper.get('.agent-trigger-card')

    expect(card.get('.agent-trigger-card__name').text()).toBe(
      'serviceType.corePeriodic'
    )
    expect(
      card.findComponent({ name: 'CorePeriodicTriggerServiceForm' }).exists()
    ).toBe(true)
    expect(card.find('.agent-trigger-card__status').exists()).toBe(false)
    expect(patches(testApp)).toEqual([])

    await choose(card.get('.dropdown'), 'periodicForm.everyDay')
    await vi.advanceTimersByTimeAsync(400)
    expect(patches(testApp)).toEqual([])

    await vi.advanceTimersByTimeAsync(100)
    await flushPromises()
    expect(patches(testApp)).toEqual([
      [
        '/agent/10/triggers/1/',
        { service: { type: 'periodic', interval: 'DAY' } },
      ],
    ])
  })

  test('saves the last service value chosen within the debounce', async () => {
    useFakeTimers()
    testApp.mock.onPatch('/agent/10/triggers/1/').reply(200, periodicTrigger())
    const wrapper = await mountSection([periodicTrigger()])
    const dropdown = wrapper.get('.agent-trigger-card .dropdown')

    await choose(dropdown, 'periodicForm.everyDay')
    await choose(dropdown, 'periodicForm.everyHour')
    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()

    expect(patches(testApp)).toEqual([
      [
        '/agent/10/triggers/1/',
        { service: { type: 'periodic', interval: 'HOUR' } },
      ],
    ])
  })

  test('shows why the service settings were rejected on the card', async () => {
    useFakeTimers()
    testApp.mock.onPatch('/agent/10/triggers/1/').reply(400, {
      error: 'ERROR_TRIGGER_SERVICE_MISCONFIGURED',
      detail: 'The schedule is invalid.',
    })
    const wrapper = await mountSection([periodicTrigger()])
    const card = wrapper.get('.agent-trigger-card')
    expect(card.find('[role="alert"]').exists()).toBe(false)

    await choose(card.get('.dropdown'), 'periodicForm.everyDay')
    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()

    expect(card.get('[role="alert"]').text()).toBe('The schedule is invalid.')
  })

  test('sends a rejected service value again with the next service edit', async () => {
    useFakeTimers()
    testApp.mock
      .onPatch('/agent/10/triggers/1/')
      .replyOnce(400, {
        error: 'ERROR_TRIGGER_SERVICE_MISCONFIGURED',
        detail: 'The schedule is invalid.',
      })
      .onPatch('/agent/10/triggers/1/')
      .reply((config) => {
        const saved = periodicTrigger()
        const body = JSON.parse(config.data)
        return [
          200,
          { ...saved, ...body, service: { ...saved.service, ...body.service } },
        ]
      })
    const wrapper = await mountSection([periodicTrigger()])
    const card = wrapper.get('.agent-trigger-card')

    await choose(card.get('.dropdown'), 'periodicForm.everyDay')
    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()
    await card.get('.agent-trigger-card__switch').trigger('click')
    await flushPromises()
    expect(card.get('[role="alert"]').text()).toBe('The schedule is invalid.')

    await card.get('input[type="number"]').setValue(9)
    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()

    expect(patches(testApp)).toEqual([
      [
        '/agent/10/triggers/1/',
        { service: { type: 'periodic', interval: 'DAY' } },
      ],
      ['/agent/10/triggers/1/', { enabled: false }],
      [
        '/agent/10/triggers/1/',
        { service: { type: 'periodic', interval: 'DAY', hour: '9' } },
      ],
    ])
    expect(card.find('[role="alert"]').exists()).toBe(false)
  })

  test('drops a rejected service value once a refetch shows the saved trigger', async () => {
    useFakeTimers()
    testApp.mock
      .onPatch('/agent/10/triggers/1/')
      .replyOnce(400, {
        error: 'ERROR_TRIGGER_SERVICE_MISCONFIGURED',
        detail: 'The schedule is invalid.',
      })
      .onPatch('/agent/10/triggers/1/')
      .replyOnce(500)
      .onPatch('/agent/10/triggers/1/')
      .reply(200, periodicTrigger())
    const wrapper = await mountSection([periodicTrigger()])

    await choose(
      wrapper.get('.agent-trigger-card .dropdown'),
      'periodicForm.everyDay'
    )
    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()
    await wrapper.get('.agent-trigger-card__switch').trigger('click')
    await flushPromises()
    const card = wrapper.get('.agent-trigger-card')
    expect(card.find('[role="alert"]').exists()).toBe(false)

    await card.get('input[type="number"]').setValue(9)
    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()

    expect(patches(testApp)).toEqual([
      [
        '/agent/10/triggers/1/',
        { service: { type: 'periodic', interval: 'DAY' } },
      ],
      ['/agent/10/triggers/1/', { enabled: false }],
      ['/agent/10/triggers/1/', { service: { type: 'periodic', minute: '9' } }],
    ])
  })

  test('switches a trigger off at once and deletes it', async () => {
    testApp.mock
      .onPatch('/agent/10/triggers/1/')
      .reply(200, periodicTrigger({ enabled: false }))
    testApp.mock.onDelete('/agent/10/triggers/1/').reply(204)
    const wrapper = await mountSection([periodicTrigger()])

    await wrapper.get('.agent-trigger-card__switch').trigger('click')
    await flushPromises()
    expect(patches(testApp)).toEqual([
      ['/agent/10/triggers/1/', { enabled: false }],
    ])
    expect(
      wrapper.get('.agent-trigger-card__switch').attributes('aria-checked')
    ).toBe('false')

    await wrapper.get('.agent-trigger-card__delete').trigger('click')
    await flushPromises()
    expect(testApp.mock.history.delete.map(({ url }) => url)).toEqual([
      '/agent/10/triggers/1/',
    ])
    expect(wrapper.find('.agent-trigger-card').exists()).toBe(false)
    expect(wrapper.text()).toContain('agent.noTriggers')
  })

  test('offers only the available trigger types that are enabled and creates the picked one', async () => {
    const service = periodicTrigger().service
    const defaults = {
      interval: 'DAY',
      hour: 9,
      minute: 0,
      timezone: moment.tz.guess(),
    }
    const created = periodicTrigger({
      id: 2,
      service: { ...service, ...defaults, id: 6 },
    })
    testApp.mock.onPost('/agent/10/triggers/').reply(200, created)
    const wrapper = await mountSection([], ['periodic', 'http_trigger'])
    expect(wrapper.text()).toContain('agent.noTriggers')

    await wrapper.get('.agent-triggers__add').trigger('click')
    await flushPromises()
    const items = wrapper
      .findComponent(AgentTriggerPicker)
      .findAll('.grouped-menu__actions .menu-list__item-button')
    expect(
      items.map((item) => item.get('.menu-list__item-label').text())
    ).toEqual(['serviceType.corePeriodic'])

    await items[0].trigger('click')
    await flushPromises()
    expect(
      testApp.mock.history.post.map(({ url, data }) => [url, JSON.parse(data)])
    ).toEqual([
      [
        '/agent/10/triggers/',
        {
          type: 'periodic',
          message: {
            formula: "concat('agent.triggerDefaultMessage ',now())",
            mode: 'advanced',
            version: '0.1',
          },
          service: defaults,
        },
      ],
    ])
    const card = wrapper.get('.agent-trigger-card')
    expect(card.find('.agent-trigger-card__status').exists()).toBe(false)
  })

  test('opens a new trigger with the translated name and the time it fired', async () => {
    const { createI18n } = await vi.importActual('vue-i18n')
    const { t } = createI18n({
      legacy: false,
      locale: 'en',
      messages: { en: { ...agentLocale, ...integrationsLocale } },
    }).global

    expect(defaultTriggerMessage(t, t('serviceType.corePeriodic'))).toEqual({
      formula: "concat('Periodic trigger fired at ',now())",
      mode: 'advanced',
      version: '0.1',
    })
  })

  test('marks an incomplete trigger on its header until it is configured', async () => {
    const service = { ...periodicTrigger().service, interval: null }
    testApp.mock.onPatch('/agent/10/triggers/1/').reply(200, periodicTrigger())
    const wrapper = await mountSection([periodicTrigger({ service })])
    const card = wrapper.get('.agent-trigger-card')

    expect(card.text()).not.toContain(
      'serviceType.corePeriodicErrorIntervalMissing'
    )
    expect(
      card.get('.agent-trigger-card__status').attributes('aria-label')
    ).toBe('serviceType.corePeriodicErrorIntervalMissing')

    await choose(card.get('.dropdown'), 'periodicForm.everyHour')

    expect(card.find('.agent-trigger-card__status').exists()).toBe(false)
  })

  test('summarises the schedule under the trigger form', async () => {
    const wrapper = await mountSection([periodicTrigger()])
    const summary = wrapper.get('.agent-trigger-card__summary')

    expect(summary.text()).toContain('serviceType.corePeriodicSummaryHour')
    expect(summary.text()).toContain('agent.triggerRunStartsConversation')
  })

  test('counts the data the trigger provides and lists it once expanded', async () => {
    const wrapper = await mountSection([periodicTrigger()])
    const toggle = wrapper.get('.agent-trigger-card__schema-toggle')

    expect(toggle.get('.agent-trigger-card__schema-title').text()).toBe(
      'agent.triggerDataProvides'
    )
    expect(toggle.get('.agent-trigger-card__schema-count').text()).toBe(
      'agent.triggerDataValues - 2'
    )
    expect(toggle.attributes('aria-expanded')).toBe('false')

    await toggle.trigger('click')

    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(
      wrapper.findAll('.agent-trigger-card__schema-list li').map((item) => {
        return item.text()
      })
    ).toEqual(['Previous scheduled runstring', 'Next scheduled runstring'])
  })

  test('edits the formula of the opening message object and keeps its mode', async () => {
    const trigger = periodicTrigger({
      message: { formula: "'Check'", mode: 'advanced', version: '0.1' },
    })
    const wrapper = await testApp.mount(AgentTriggerMessageInput, {
      props: { modelValue: trigger.message },
      global: {
        provide: { applicationContext: reactive({ agent, trigger }) },
      },
    })
    const field = wrapper.findComponent(FormulaInputField)
    expect([field.props('value'), field.props('mode')]).toEqual([
      "'Check'",
      'advanced',
    ])

    field.vm.$emit('input', "'Daily check'")
    expect(wrapper.emitted('update:modelValue')).toEqual([
      [{ formula: "'Daily check'", mode: 'advanced', version: '0.1' }],
    ])
  })

  test('offers the trigger payload as formula variables in the opening message', async () => {
    const trigger = periodicTrigger()
    const wrapper = await testApp.mount(AgentTriggerMessageInput, {
      props: { modelValue: trigger.message },
      global: {
        provide: { applicationContext: reactive({ agent, trigger }) },
      },
    })
    const [dataGroup] = wrapper
      .findComponent(FormulaInputField)
      .props('nodesHierarchy')

    expect(dataGroup.type).toBe('data')
    expect(dataGroup.nodes.map((node) => node.identifier)).toEqual(['trigger'])
    expect(dataGroup.nodes[0].name).toBe('agent.triggerData')
    expect(dataGroup.nodes[0].nodes.map((node) => node.name)).toEqual([
      'Previous scheduled run',
      'Next scheduled run',
    ])
  })
})
