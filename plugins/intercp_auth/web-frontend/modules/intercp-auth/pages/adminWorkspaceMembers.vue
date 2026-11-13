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

<script>
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

export default {
  name: 'AdminWorkspaceMembers',
  components: { PaginatedDropdown },
  setup() {
    const { $i18n } = useNuxtApp()
    useHead({ title: $i18n.t('intercpWorkspaceMembers.title') })
  },
  data() {
    return {
      workspaceId: null,
      userId: null,
      permissions: 'MEMBER',
      loading: false,
    }
  },
  methods: {
    fetchWorkspaces(page, search) {
      return fetchWorkspaceOptions(this.$client, page, search)
    },
    fetchUsers(page, search) {
      const service = UsersAdminService(this.$client)
      return service.fetch(service.options.baseUrl, page, search, [], {})
    },
    userName(user) {
      return `${user.name} (${user.username})`
    },
    async add() {
      this.loading = true
      try {
        const { data } = await this.$client.post(
          '/intercp/admin/workspace-members/',
          {
            workspace_id: this.workspaceId,
            user_id: this.userId,
            permissions: this.permissions,
          }
        )
        const message = data.added
          ? this.$t('intercpWorkspaceMembers.added')
          : this.$t('intercpWorkspaceMembers.alreadyMember')
        await this.$store.dispatch('toast/success', { title: message })
      } catch (error) {
        notifyIf(error)
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
