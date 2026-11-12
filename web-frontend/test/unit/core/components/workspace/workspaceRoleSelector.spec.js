import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, test } from 'vitest'

import WorkspaceRoleSelector from '@baserow/modules/core/components/workspace/WorkspaceRoleSelector'

const workspace = { id: 12 }
const roles = [
  { uid: 'MEMBER', name: 'Member' },
  { uid: 'ADMIN', name: 'Admin' },
]

describe('WorkspaceRoleSelector', () => {
  test('lists every role', async () => {
    const wrapper = await mountSuspended(WorkspaceRoleSelector, {
      props: {
        modelValue: 'MEMBER',
        workspace,
        roles,
      },
      global: {
        stubs: {
          Dropdown: { template: '<div><slot /></div>' },
          DropdownItem: {
            template: '<div class="dropdown-item"><slot /></div>',
          },
        },
      },
    })

    expect(
      wrapper.findAll('.dropdown-item').map((item) => item.text())
    ).toEqual(['Member', 'Admin'])
  })
})

test('uses role metadata for the selected icon and can hide it', async () => {
  const wrapper = await mountSuspended(WorkspaceRoleSelector, {
    props: {
      workspace,
      modelValue: 'CUSTOM',
      roles: [{ uid: 'CUSTOM', name: 'Custom role', icon: 'iconoir-star' }],
      showRoleIcons: true,
    },
    global: { mocks: { $registry: { getAll: () => ({}) } } },
  })
  expect(wrapper.get('.dropdown__selected-icon').classes()).toContain(
    'iconoir-star'
  )
  await wrapper.setProps({ showRoleIcons: false })
  expect(wrapper.find('.dropdown__selected-icon').exists()).toBe(false)
  wrapper.unmount()
})
