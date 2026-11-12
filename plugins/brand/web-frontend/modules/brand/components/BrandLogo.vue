<template>
  <div class="logo">
    <!-- Served from the brand folder when it holds a logo.svg, else core's. -->
    <img src="/img/logo.svg" :alt="$config.public.brandName" v-bind="$attrs" />
  </div>
</template>

<script>
export default {
  name: 'BrandLogo',
  // Core's Logo.vue passes height/alt through; they belong on the image.
  inheritAttrs: false,
}
</script>
