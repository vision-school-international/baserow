<template>
  <li>
    <a
      class="choice-items__link"
      :class="{ active, disabled }"
      @click="!disabled && $emit('selected')"
    >
      <i class="choice-items__icon" :class="dataSyncType.iconClass"></i>
      <span> {{ dataSyncType.getName() }}</span>
      <i
        v-if="active"
        class="choice-items__icon-active iconoir-check-circle"
      ></i>
    </a>
  </li>
</template>
<script>
export default {
  name: 'DataSyncTypeChoice',
  props: {
    dataSyncType: {
      required: true,
      type: Object,
    },
    active: {
      required: true,
      type: Boolean,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['selected'],
}
</script>
