import { TestApp } from '@baserow/test/helpers/testApp'
import FormViewFooterLinks from '@baserow/modules/database/components/view/form/FormViewFooterLinks'

describe('FormViewFooterLinks', () => {
  let testApp = null

  beforeEach(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  async function mountFooter(propsData = {}) {
    return await testApp.mount(FormViewFooterLinks, { propsData })
  }

  test('renders nothing when reporting is not requested', async () => {
    const wrapper = await mountFooter()

    expect(wrapper.find('.form-view__footer-links').exists()).toBe(false)
  })

  test('shows the report link when requested', async () => {
    const wrapper = await mountFooter({
      showReportAbuse: true,
      identifier: 'test-slug',
    })

    expect(wrapper.find('.form-view__report-abuse').exists()).toBe(true)
  })

  test('does not show the report link when reporting is disabled instance wide', async () => {
    testApp.store.commit('settings/SET_SETTINGS', {
      allow_reporting_abuse: false,
    })

    const wrapper = await mountFooter({
      showReportAbuse: true,
      identifier: 'test-slug',
    })

    expect(wrapper.find('.form-view__report-abuse').exists()).toBe(false)
  })
})
