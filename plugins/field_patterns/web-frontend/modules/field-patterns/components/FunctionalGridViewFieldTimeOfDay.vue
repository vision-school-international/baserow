<template>
  <div class="grid-view__cell">
    <div class="grid-field-text">{{ display }}</div>
  </div>
</template>

<script>
import { formatTime } from '../time'

/** Core's FunctionalGridViewFieldText, in the field's clock. */
export default {
  name: 'FunctionalGridViewFieldTimeOfDay',
  props: {
    value: { type: String, default: '' },
    field: { type: Object, required: true },
  },
  computed: {
    display() {
      return formatTime(this.value, this.field.time_format)
    },
  },
}
</script>
