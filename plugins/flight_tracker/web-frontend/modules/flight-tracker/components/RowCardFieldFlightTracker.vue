<template>
  <div class="card-text">{{ trackerText }}</div>
</template>

<script>
import trackerCellMixin from '../trackerCellMixin'

export default {
  name: 'RowCardFieldFlightTracker',
  mixins: [trackerCellMixin],
  height: 16,
  props: {
    value: { type: Object, default: null },
    field: { type: Object, required: true },
    row: { type: Object, default: null },
  },
}
</script>
