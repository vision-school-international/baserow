<template>
  <a v-if="brandUrl" :href="brandUrl" target="_blank" :title="brandName">
    <Logo height="14" :alt="brandName" />
  </a>
  <Logo v-else height="14" :alt="brandName" />
</template>

<script>
export default {
  name: 'ExternalLinkBaserowLogo',
  computed: {
    // Set by the brand plugin (plugins/brand). No URL means no link.
    brandName() {
      return this.$config.public.brandName || 'Baserow'
    },
    brandUrl() {
      return this.$config.public.brandUrl || ''
    },
  },
}
</script>
