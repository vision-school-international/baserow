<template>
  <Logo height="14" :alt="$config.public.brandName || 'Baserow'" />
</template>

<script>
// The logo never links anywhere.
export default {
  name: 'ExternalLinkBaserowLogo',
}
</script>
