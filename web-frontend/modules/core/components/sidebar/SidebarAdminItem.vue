<template>
  <li
    class="tree__item"
    :class="{
      active: $route.matched.some(({ name }) => name === adminType.routeName),
    }"
  >
    <div
      class="tree__action sidebar__action"
      :class="{ 'tree__action--has-counter': badgeCount > 0 }"
    >
      <nuxt-link :to="{ name: adminType.routeName }" class="tree__link">
        <i class="tree__icon" :class="adminType.iconClass"></i>
        <span class="tree__link-text">
          <span class="sidebar__item-name">{{ adminType.getName() }}</span>
        </span>
      </nuxt-link>
      <BadgeCounter
        v-if="badgeCount > 0"
        class="tree__counter badge-counter--warning"
        :count="badgeCount"
        :limit="10"
      ></BadgeCounter>
    </div>
  </li>
</template>

<script>
import BadgeCounter from '@baserow/modules/core/components/BadgeCounter'

export default {
  name: 'SidebarAdminItem',
  components: { BadgeCounter },
  props: {
    adminType: {
      required: true,
      type: Object,
    },
  },
  computed: {
    adminTypeObject() {
      return this.$registry.get('admin', this.adminType.type)
    },
    badgeCount() {
      return this.adminTypeObject.getBadgeCount()
    },
  },
  mounted() {
    this.adminTypeObject.loadBadgeCount()
  },
}
</script>
