import { describe, expect, test, vi } from 'vitest'
import { AgentApplicationType } from '@baserow/modules/agent/applicationTypes'
import { AgentLastViewedItemType } from '@baserow/modules/agent/lastViewedItemTypes'

describe('AgentApplicationType', () => {
  const agent = { id: 10, type: 'agent', workspace: { id: 1 } }

  function makeType({ flagEnabled = true, selected = false } = {}) {
    const app = {
      $featureFlagIsEnabled: (flag) => flagEnabled && flag === 'agent-builder',
      $router: { push: vi.fn() },
      $store: { getters: { 'application/isSelected': () => selected } },
    }
    return { type: new AgentApplicationType({ app }), app }
  }

  test.each([true, false])(
    'can be created only while the rollout flag is enabled=%s',
    (enabled) => {
      expect(makeType({ flagEnabled: enabled }).type.canBeCreated()).toBe(
        enabled
      )
    }
  )

  test.each([true, false])(
    'offers the recently viewed filter only while the rollout flag is enabled=%s',
    (enabled) => {
      const { type, app } = makeType({ flagEnabled: enabled })
      app.$i18n = { t: (key) => key }
      app.$registry = { get: () => type }
      const lastViewedType = new AgentLastViewedItemType({ app })

      expect(
        lastViewedType.getFilterOptions().map(({ value }) => value)
      ).toEqual(enabled ? ['agent'] : [])
    }
  )

  test('opens the agent route by application ID', async () => {
    const { type, app } = makeType()

    expect(await type.select(agent)).toBe(true)
    expect(app.$router.push).toHaveBeenCalledWith({
      name: 'agent-application',
      params: { agentId: 10 },
    })
  })

  test.each([true, false])(
    'returns to the workspace when the deleted agent is selected=%s',
    (selected) => {
      const { type, app } = makeType({ selected })

      type.delete(agent)

      expect(app.$router.push.mock.calls).toEqual(
        selected ? [[{ name: 'workspace', params: { workspaceId: 1 } }]] : []
      )
    }
  )

  test.each([
    ['a private conversation', 'agent_conversation', 7, ['restore']],
    [
      'a shared conversation',
      'agent_conversation',
      null,
      ['restore', 'update'],
    ],
    ['a trigger', 'agent_trigger', null, ['update']],
  ])('restoring %s needs only its operations', (_, itemType, owner, needed) => {
    const operations = {
      restore: 'agent_application.restore_conversation',
      update: 'application.update',
    }
    const entry = { trash_item_type: itemType, trash_item_owner: owner }
    const { type, app } = makeType()
    const allows = (granted) => {
      app.$hasPermission = vi.fn((operation, context, workspaceId) =>
        Boolean(
          context === agent && workspaceId === 1 && granted.has(operation)
        )
      )
      return type.canRestoreTrashEntry(agent, entry, 1)
    }

    expect(allows(new Set(needed.map((key) => operations[key])))).toBe(true)
    for (const key of needed) {
      const granted = new Set(
        needed
          .filter((other) => other !== key)
          .map((other) => operations[other])
      )
      expect(allows(granted)).toBe(false)
    }
  })
})
