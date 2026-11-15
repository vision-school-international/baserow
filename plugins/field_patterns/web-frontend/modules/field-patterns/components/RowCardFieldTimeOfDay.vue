<template>
  <div class="card-text">
    {{ display }}
  </div>
</template>

<script>
import { formatTime } from '../time'

/** Core's RowCardFieldText, in the field's clock. */
export default {
  name: 'RowCardFieldTimeOfDay',
  height: 16,
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
