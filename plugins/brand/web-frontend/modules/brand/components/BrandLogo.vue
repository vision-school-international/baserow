<template>
  <div class="logo">
    <!-- Served from the brand plugin's public/img folder. -->
    <img src="/img/logo.png" :alt="$config.public.brandName" v-bind="$attrs" />
  </div>
</template>

<script>
export default {
  name: 'BrandLogo',
  // Core's Logo.vue passes height/alt through; they belong on the image.
  inheritAttrs: false,
}
</script>
