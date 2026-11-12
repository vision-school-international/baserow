<template>
  <div></div>
</template>

<script setup>
// Login only: accounts are created by signing in with Telegram, so /signup goes to
// the login page. The query keeps workspace invitation tokens and link slugs.
const route = useRoute()
await navigateTo({ name: 'login', query: route.query }, { replace: true })
</script>
