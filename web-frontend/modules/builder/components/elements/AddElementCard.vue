<template>
  <div
    :key="elementType.name"
    v-tooltip="disabled ? isDisallowedReason : elementType.description"
    class="add-element-card"
    :class="{ 'add-element-card--disabled': disabled }"
    @click.stop="onClick"
  >
    <div class="add-element-card__element-type">
      <img
        class="add-element-card__element-type-icon"
        :src="elementType.image"
      />
    </div>
    <div v-if="loading" class="loading"></div>
    <span v-else class="add-element-card__label">{{ elementType.name }}</span>
  </div>
</template>

<script>
export default {
  name: 'AddElementCard',
  props: {
    elementType: {
      type: Object,
      required: true,
    },
    workspace: {
      type: Object,
      required: true,
    },
    builder: {
      type: Object,
      required: true,
    },
    page: {
      type: Object,
      required: true,
    },
    placeInContainer: {
      type: String,
      required: false,
      default: undefined,
    },
    parentElement: {
      type: Object,
      required: false,
      default: undefined,
    },
    beforeElement: {
      type: Object,
      required: false,
      default: undefined,
    },
    afterElement: {
      type: Object,
      required: false,
      default: undefined,
    },
    pagePlace: {
      type: String,
      required: false,
      default: undefined,
    },
    loading: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  emits: ['click'],
  computed: {
    isDisallowedReason() {
      return this.elementType.isDisallowedReason({
        workspace: this.workspace,
        builder: this.builder,
        page: this.page,
        placeInContainer: this.placeInContainer,
        parentElement: this.parentElement,
        beforeElement: this.beforeElement,
        afterElement: this.afterElement,
        pagePlace: this.pagePlace,
      })
    },
    disabled() {
      return !!this.isDisallowedReason
    },
  },
  methods: {
    onClick(event) {
      if (!this.disabled) {
        this.$emit('click', event)
      }
    },
  },
}
</script>
