<template>
  <div class="management-pages">
    <Tabs offset full-height :route="route" large-offset>
      <Tab
        v-for="page in pages"
        :key="page.type"
        :title="page.name"
        :badge="page.badge"
        :to="page.to"
        :development-stage="page.developmentStage"
      >
        <NuxtPage :workspace="workspace" />
      </Tab>
    </Tabs>
  </div>
</template>

<script setup>
import { useHead } from '#imports'

/* Using Vuex in Nuxt 3 with Composition API */

const route = useRoute()
const router = useRouter()
const nuxtApp = useNuxtApp()
const store = nuxtApp.$store
const { $i18n } = nuxtApp

/* asyncData → useAsyncData */
const { data: workspace, error } = await useAsyncData('workspace', async () => {
  try {
    return await store.dispatch(
      'workspace/selectById',
      parseInt(route.params.workspaceId, 10)
    )
  } catch (e) {
    throw createError({
      statusCode: 404,
      message: 'Workspace not found.',
      data: {
        report: false,
      },
      fatal: true,
    })
  }
})

if (error.value) {
  throw error.value
}

/* Registry access */
const registry = nuxtApp.$registry

/* Build settings pages */
const workspaceSettingsPageTypes = computed(() =>
  registry.getOrderedList('workspaceSettingsPage')
)

/* Build an array of settings page types they're permitted to view. */
const pages = computed(() => {
  const permittedPages = workspaceSettingsPageTypes.value.filter((instance) =>
    instance.hasPermission(workspace.value)
  )

  return permittedPages.map((instance) => ({
    type: instance.type,
    name: instance.getName(),
    developmentStage: instance.developmentStage,
    badge: instance.getBadge(),
    to: instance.getRoute(workspace.value),
  }))
})

/* Dynamic page title based on current tab */
const currentPageName = computed(() => {
  const currentPage = pages.value.find((p) => p.to?.name === route.name)
  return currentPage?.name || $i18n.t('sidebar.settings')
})

useHead(() => ({
  title: currentPageName.value,
}))

/* Event bus */
const bus = nuxtApp.$bus

function workspaceDeleted() {
  router.push({ name: 'all-workspaces' })
}

onMounted(() => {
  bus.$on('workspace-deleted', workspaceDeleted)
})

onBeforeUnmount(() => {
  bus.$off('workspace-deleted', workspaceDeleted)
})
</script>
