<template>
  <div v-if="workspaceExists">
    <div class="dashboard__header" ph-autocapture="dashboard-header">
      <div class="dashboard__header-left">
        <h1
          ref="contextLink"
          class="dashboard__workspace-name"
          @click="
            $refs.context.toggle($refs.contextLink, 'bottom', 'left', -14)
          "
        >
          <div class="dashboard__workspace-name-text">
            <Editable
              ref="rename"
              :value="selectedWorkspace.name"
              @change="renameWorkspace(selectedWorkspace, $event)"
            >
            </Editable>
          </div>
          <i class="dashboard__workspace-name-icon iconoir-nav-arrow-down"></i>
        </h1>
      </div>
      <WorkspaceContext
        ref="context"
        :workspace="selectedWorkspace"
        @rename="enableRename()"
      ></WorkspaceContext>
      <div class="dashboard__header-right">
        <div class="dashboard__header-actions">
          <SkeletonBlock
            v-if="!permissionsLoaded"
            width="100px"
            height="32px"
          ></SkeletonBlock>
          <span
            v-else-if="canCreateCreateApplication"
            ref="createApplicationContextLink"
          >
            <Button
              icon="iconoir-plus"
              tag="a"
              @click="
                $refs.createApplicationContext.toggle(
                  $refs.createApplicationContextLink
                )
              "
              >{{ $t('dashboard.addNew') }}</Button
            >
          </span>
          <span
            ref="workspaceContextLink"
            @click="
              $refs.context.toggle(
                $refs.workspaceContextLink,
                'bottom',
                'right',
                4
              )
            "
          >
            <ButtonIcon
              type="secondary"
              icon="baserow-icon-more-vertical"
            ></ButtonIcon>
          </span>
        </div>
      </div>
    </div>
    <div
      class="dashboard__scroll-container"
      ph-autocapture="dashboard-container"
    >
      <div class="dashboard__main">
        <component
          :is="component"
          v-for="(component, index) in dashboardTopComponents"
          :key="index"
          :workspace="selectedWorkspace"
        ></component>
        <div class="dashboard__extras">
          <div class="dashboard__resources">
            <div class="dashboard__resources-wrapper">
              <component
                :is="component"
                v-for="(component, index) in resourceLinksComponents"
                :key="index"
              ></component>
            </div>
          </div>
        </div>
        <div class="dashboard__wrapper">
          <RecentlyViewed
            v-if="orderedApplicationsInSelectedWorkspace.length"
            :workspace="selectedWorkspace"
            :title="$t('recentlyViewed.yourItems')"
            view-mode-preference-key="workspace_recently_viewed_view_mode"
          >
            <template #empty-action>
              <span
                v-if="canCreateCreateApplication"
                ref="createApplicationContextLink2"
              >
                <Button
                  icon="iconoir-plus"
                  tag="a"
                  @click="
                    $refs.createApplicationContext.toggle(
                      $refs.createApplicationContextLink2
                    )
                  "
                  >{{ $t('dashboard.addNew') }}</Button
                >
              </span>
            </template>
          </RecentlyViewed>
          <div v-else class="dashboard__no-application">
            <img
              src="@baserow/modules/core/assets/images/empty_workspace_illustration.png"
              srcset="
                @baserow/modules/core/assets/images/empty_workspace_illustration@2x.png 2x
              "
            />
            <h4>{{ $t('dashboard.emptyWorkspace') }}</h4>
            <p v-if="canCreateCreateApplication">
              {{ $t('dashboard.emptyWorkspaceMessage') }}
            </p>
            <SkeletonBlock
              v-if="!permissionsLoaded"
              width="100px"
              height="32px"
            ></SkeletonBlock>
            <span
              v-else-if="canCreateCreateApplication"
              ref="createApplicationContextLink2"
            >
              <Button
                icon="iconoir-plus"
                tag="a"
                @click="
                  $refs.createApplicationContext.toggle(
                    $refs.createApplicationContextLink2
                  )
                "
                >{{ $t('dashboard.addNew') }}</Button
              >
            </span>
          </div>
        </div>
      </div>
      <CreateApplicationContext
        ref="createApplicationContext"
        :workspace="selectedWorkspace"
      >
      </CreateApplicationContext>
    </div>
    <component
      :is="component"
      v-for="(component, index) in dashboardHelpComponents"
      :key="index"
    ></component>
  </div>
</template>

<script setup>
import { ref, computed, watchEffect } from 'vue'
import { useRoute, useNuxtApp, createError } from '#app'
import { useHead } from '#imports'
import { usePageAsyncData } from '@baserow/modules/core/composables/usePageAsyncData'

import { StoreItemLookupError } from '@baserow/modules/core/errors'

import WorkspaceContext from '@baserow/modules/core/components/workspace/WorkspaceContext'
import CreateApplicationContext from '@baserow/modules/core/components/application/CreateApplicationContext'
import RecentlyViewed from '@baserow/modules/core/components/recentlyViewed/RecentlyViewed'
import editWorkspace from '@baserow/modules/core/mixins/editWorkspace'

definePageMeta({
  layout: 'app',
  // Note: these middlewares must be explicitly listed because child pages
  // don't automatically inherit parent middleware in Nuxt 3's page meta
  middleware: [
    'settings',
    'authenticated',
    'impersonate',
    'workspacesAndApplications',
  ],
})

defineOptions({
  mixins: [editWorkspace],
})

const route = useRoute()
const nuxtApp = useNuxtApp()
const { $store, $registry, $i18n, $hasPermission } = nuxtApp

// ----------------------------------------------------------------------------
// STATE
// ----------------------------------------------------------------------------
// The workspaces are already in the store, so the page can render its header and
// applications right away, while the rest is being fetched.
const selectedWorkspace = ref(
  $store.getters['workspace/getAll'].find(
    (workspace) => workspace.id === parseInt(route.params.workspaceId, 10)
  ) || null
)

// refs used in template
const context = ref(null)
const contextLink = ref(null)
const createApplicationContext = ref(null)
const workspaceContextLink = ref(null)
const createApplicationContextLink2 = ref(null)
const rename = ref(null)

/**
 * Selects the workspace. The ref below is hydrated from it.
 */
const { data: dashboardData } = await usePageAsyncData(
  `current-workspace-${route.params.workspaceId}`,
  async () => {
    const workspaceId = parseInt(route.params.workspaceId, 10)

    let workspace
    try {
      workspace = await $store.dispatch('workspace/selectById', workspaceId)
    } catch (e) {
      // Only an unknown workspace is a not found error. Any other failure, like a
      // transient permissions fetch error, is a loading error.
      if (e instanceof StoreItemLookupError) {
        throw createError({
          statusCode: 404,
          message: 'Workspace not found.',
          data: {
            report: false,
          },
          fatal: true,
        })
      }
      throw createError({
        statusCode: 400,
        message: 'Error loading dashboard.',
        data: {
          report: false,
        },
        fatal: true,
      })
    }

    return { selectedWorkspace: workspace }
  }
)

/**
 * Hydrate the local ref from the async data, keeping `selectedWorkspace`
 * reactive and writable.
 */
watchEffect(() => {
  if (!dashboardData.value) return
  selectedWorkspace.value = dashboardData.value.selectedWorkspace
})

useHead(() => ({
  title: $i18n.t('dashboard.title'),
}))

const getAllOfWorkspace = (ws) =>
  $store.getters['application/getAllOfWorkspace'](ws)

const dashboardHelpComponents = computed(() =>
  Object.values($registry.getAll('plugin'))
    .reduce(
      (components, plugin) =>
        components.concat(plugin.getDashboardHelpComponents()),
      []
    )
    .filter((c) => c !== null)
)

const dashboardTopComponents = computed(() =>
  Object.values($registry.getAll('plugin'))
    .reduce(
      (components, plugin) =>
        components.concat(
          plugin.getDashboardTopComponents(selectedWorkspace.value)
        ),
      []
    )
    .filter((c) => c !== null)
)

const resourceLinksComponents = computed(() =>
  Object.values($registry.getAll('plugin'))
    .map((p) => p.getDashboardResourceLinksComponent())
    .filter((c) => c !== null)
)

const orderedApplicationsInSelectedWorkspace = computed(() =>
  !selectedWorkspace.value
    ? []
    : getAllOfWorkspace(selectedWorkspace.value).sort(
        (a, b) => a.order - b.order
      )
)

const permissionsLoaded = computed(
  () =>
    !!selectedWorkspace.value &&
    $store.getters['workspace/haveWorkspacePermissionsBeenLoaded'](
      selectedWorkspace.value.id
    )
)

const canCreateCreateApplication = computed(() => {
  if (!selectedWorkspace.value) return false
  return $hasPermission(
    'workspace.create_application',
    selectedWorkspace.value,
    selectedWorkspace.value.id
  )
})

/**
 * Check if the workspace exists, because if not, it doesn't make any sense to
 * render anything. This can happen when the workspace is a state where it's
 * deleted, for example.
 */
const workspaceExists = computed(() => {
  if (!selectedWorkspace.value) return false
  return $store.getters['workspace/getAll'].some(
    (w) => w.id === selectedWorkspace.value.id
  )
})
</script>
