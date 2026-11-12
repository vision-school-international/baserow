<template>
  <a
    class="create-widget-card"
    :class="{ 'create-widget-card--disabled': disabled }"
    :aria-disabled="disabled"
    @click="widgetVariationSelected"
  >
    <div class="create-widget-card__img-container">
      <img :src="variation.createWidgetImage" />
    </div>
    <div class="create-widget-card__name">
      <span>{{ variation.name }}</span>
    </div>
  </a>
</template>

<script>
export default {
  name: 'CreateWidgetCard',
  props: {
    variation: {
      type: Object,
      required: true,
    },
    disabled: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  emits: ['widget-variation-selected'],
  methods: {
    widgetVariationSelected() {
      if (this.disabled) {
        return
      }

      this.$emit('widget-variation-selected', this.variation)
    },
  },
}
</script>
