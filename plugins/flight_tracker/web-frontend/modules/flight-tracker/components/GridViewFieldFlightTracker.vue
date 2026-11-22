<template>
  <div ref="cell" class="grid-view__cell active">
    <div class="grid-field-text">{{ text }}</div>
  </div>
</template>

<script>
import gridField from '@baserow/modules/database/mixins/gridField'
import { summary } from '../tracker'

/** Selected, like core's GridViewFieldUUID: read only. */
export default {
  name: 'GridViewFieldFlightTracker',
  mixins: [gridField],
  computed: {
    text() {
      return summary(this.value, this.$t)
    },
  },
}
</script>
