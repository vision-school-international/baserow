import { mount } from '@vue/test-utils'

import CreateWidgetCard from '@baserow/modules/dashboard/components/CreateWidgetCard'

function mountCreateWidgetCard(disabled) {
  return mount(CreateWidgetCard, {
    props: {
      variation: {
        name: 'Summary',
        createWidgetImage: '',
      },
      disabled,
    },
  })
}

describe('CreateWidgetCard', () => {
  test('does not select a widget while creation is pending', async () => {
    const wrapper = mountCreateWidgetCard(true)

    await wrapper.trigger('click')

    expect(wrapper.emitted('widget-variation-selected')).toBeUndefined()
    expect(wrapper.attributes('aria-disabled')).toBe('true')
  })

  test('selects an available widget when creation is not pending', async () => {
    const wrapper = mountCreateWidgetCard(false)

    await wrapper.trigger('click')

    expect(wrapper.emitted('widget-variation-selected')).toEqual([
      [wrapper.props('variation')],
    ])
  })
})
