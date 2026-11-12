<template>
  <a :href="brandUrl" target="_blank" :title="brandName">
    <Logo height="14" :alt="brandName" />
  </a>
</template>

<script>
export default {
  name: 'ExternalLinkBaserowLogo',
  computed: {
    // Set by the brand plugin (plugins/brand); defaults to Baserow without it.
    brandName() {
      return this.$config.public.brandName || 'Baserow'
    },
    brandUrl() {
      return this.$config.public.brandUrl || 'https://baserow.io'
    },
  },
}
</script>
