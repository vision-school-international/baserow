<template>
  <div class="grid-view__cell">
    <div class="grid-field-text">
      {{ value }}
      <span v-if="flightText" class="flight-tracker__status">
        {{
          [flightText.state, flightText.route, flightText.delay]
            .filter(Boolean)
            .join(' · ')
        }}
      </span>
    </div>
  </div>
</template>

<script>
import flightStatusMixin from '../flightStatusMixin'

/** Core's FunctionalGridViewFieldText, with the flight's status after it. */
export default {
  name: 'FunctionalGridViewFieldFlight',
  mixins: [flightStatusMixin],
  props: {
    value: { type: String, default: '' },
    field: { type: Object, required: true },
    row: { type: Object, default: null },
  },
}
</script>
