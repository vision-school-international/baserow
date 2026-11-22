<template>
  <div class="grid-view__cell">
    <div class="grid-field-text">{{ trackerText }}</div>
  </div>
</template>

<script>
import trackerCellMixin from '../trackerCellMixin'

/** The cell's one-line summary; the JSON is the full data. */
export default {
  name: 'FunctionalGridViewFieldFlightTracker',
  mixins: [trackerCellMixin],
  props: {
    value: { type: Object, default: null },
    field: { type: Object, required: true },
    row: { type: Object, default: null },
  },
}
</script>
