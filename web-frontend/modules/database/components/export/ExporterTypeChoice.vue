<template>
  <li>
    <a
      class="choice-items__link"
      :class="{ active, disabled }"
      @click="select(exporterType)"
    >
      <i class="choice-items__icon" :class="exporterType.iconClass"></i>
      <span>{{ exporterType.getName() }}</span>
      <i
        v-if="active"
        class="choice-items__icon-active iconoir-check-circle"
      ></i>
    </a>
  </li>
</template>

<script>
export default {
  name: 'ExporterTypeChoice',
  props: {
    exporterType: {
      required: true,
      type: Object,
    },
    active: {
      required: true,
      type: Boolean,
    },
    disabled: {
      required: true,
      type: Boolean,
    },
  },
  emits: ['selected'],
  methods: {
    select(exporterType) {
      if (!this.disabled) {
        this.$emit('selected', exporterType)
      }
    },
  },
}
</script>
