<template>
  <div class="layout__col-2-scroll">
    <div class="admin-settings">
      <h1>{{ $t('intercpWorkspaceMembers.title') }}</h1>
      <div class="admin-settings__group">
        <div class="admin-settings__item">
          <div class="admin-settings__label">
            <div class="admin-settings__name">
              {{ $t('intercpWorkspaceMembers.workspace') }}
            </div>
          </div>
          <div class="admin-settings__control">
            <PaginatedDropdown
              :value="workspaceId"
              :fetch-page="fetchWorkspaces"
              :add-empty-item="false"
              :not-selected-text="$t('intercpWorkspaceMembers.chooseWorkspace')"
              value-name="name"
              @input="workspaceId = $event"
            />
          </div>
        </div>
        <div class="admin-settings__item">
          <div class="admin-settings__label">
            <div class="admin-settings__name">
              {{ $t('intercpWorkspaceMembers.user') }}
            </div>
          </div>
          <div class="admin-settings__control">
            <PaginatedDropdown
              :value="userId"
              :fetch-page="fetchUsers"
              :add-empty-item="false"
              :not-selected-text="$t('intercpWorkspaceMembers.chooseUser')"
              :value-name="userName"
              @input="userId = $event"
            />
          </div>
        </div>
        <div class="admin-settings__item">
          <div class="admin-settings__label">
            <div class="admin-settings__name">
              {{ $t('intercpWorkspaceMembers.role') }}
            </div>
          </div>
          <div class="admin-settings__control">
            <Dropdown v-model="permissions" :show-search="false">
              <DropdownItem
                :name="$t('intercpWorkspaceMembers.member')"
                value="MEMBER"
              />
              <DropdownItem
                :name="$t('intercpWorkspaceMembers.admin')"
                value="ADMIN"
              />
            </Dropdown>
          </div>
        </div>
        <div class="admin-settings__item">
          <div class="admin-settings__label"></div>
          <div class="admin-settings__control">
            <Button
              type="primary"
              :loading="loading"
              :disabled="loading || !workspaceId || !userId"
              @click="add"
            >
              {{ $t('intercpWorkspaceMembers.add') }}
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useHead } from '#imports'
import { useNuxtApp } from '#app'
import PaginatedDropdown from '@baserow/modules/core/components/PaginatedDropdown'
import { fetchWorkspaceOptions } from '@baserow/modules/core/services/admin/workspaces'
import UsersAdminService from '@baserow/modules/core/services/admin/users'
import { notifyIf } from '@baserow/modules/core/utils/error'

// Same layout and middleware as core's admin pages (pages/admin/settings.vue).
definePageMeta({
  layout: 'app',
  middleware: 'staff',
})

// Same composition pattern as core/pages/login.vue:22 and resetPassword.vue:106.
const { $store: store, $client } = useNuxtApp()
const i18n = useI18n()
useHead({ title: i18n.t('intercpWorkspaceMembers.title') })

const workspaceId = ref(null)
const userId = ref(null)
const permissions = ref('MEMBER')
const loading = ref(false)

function fetchWorkspaces(page, search) {
  return fetchWorkspaceOptions($client, page, search)
}

async function fetchUsers(page, search) {
  const service = UsersAdminService($client)
  const response = await service.fetch(
    service.options.baseUrl,
    page,
    search,
    [],
    {}
  )
  // The backend only accepts active users, and the admin users endpoint has no
  // filter for it (api/admin/users/views.py). `count` stays, so paging goes on.
  response.data.results = response.data.results.filter((user) => user.is_active)
  return response
}

function userName(user) {
  return `${user.name} (${user.username})`
}

async function add() {
  loading.value = true
  try {
    const { data } = await $client.post('/intercp/admin/workspace-members/', {
      workspace_id: workspaceId.value,
      user_id: userId.value,
      permissions: permissions.value,
    })
    const message = data.added
      ? i18n.t('intercpWorkspaceMembers.added')
      : i18n.t('intercpWorkspaceMembers.alreadyMember')
    await store.dispatch('toast/success', { title: message })
  } catch (error) {
    notifyIf(error)
  } finally {
    loading.value = false
  }
}
</script>
