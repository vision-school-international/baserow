import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, test } from 'vitest'

import EditRoleContext from '@baserow/modules/core/components/settings/members/EditRoleContext'

const workspace = { id: 12 }
const subject = { id: 34, role_uid: 'MEMBER' }
const roles = [
  { uid: 'MEMBER', name: 'Member', isVisible: true },
  { uid: 'ADMIN', name: 'Admin', isVisible: true },
  { uid: 'HIDDEN', name: 'Hidden', isVisible: false },
]

const mountContext = () =>
  mountSuspended(EditRoleContext, {
    props: {
      workspace,
      subject,
      roles,
      roleValueColumn: 'role_uid',
    },
    global: {
      mocks: {
        $t: (key) => key,
      },
      stubs: {
        Context: { template: '<div><slot /></div>' },
      },
    },
  })

describe('EditRoleContext', () => {
  test('lists the visible roles and marks the current one', async () => {
    const wrapper = await mountContext()

    const titles = wrapper
      .findAll('.context__menu-item-title')
      .map((title) => title.text())
    expect(titles).toEqual(['Member', 'Admin'])
    const links = wrapper.findAll('.context__menu-item-link')
    expect(links[0].classes()).toContain('active')
    expect(links[1].classes()).not.toContain('active')
  })

  test('emits the new role when another role is clicked', async () => {
    const wrapper = await mountContext()

    await wrapper.findAll('.context__menu-item-link')[1].trigger('click')

    expect(wrapper.emitted('update-role')).toEqual([
      [{ uid: 'ADMIN', subject }],
    ])
  })
})
