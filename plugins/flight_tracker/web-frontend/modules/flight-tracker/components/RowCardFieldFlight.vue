<template>
  <div class="card-text">
    {{ value }}
    <span v-if="flightText" class="flight-tracker__status">
      {{ [flightText.state, flightText.route].filter(Boolean).join(' · ') }}
    </span>
  </div>
</template>

<script>
import flightStatusMixin from '../flightStatusMixin'

/** Core's RowCardFieldText, with the flight's status after it. */
export default {
  name: 'RowCardFieldFlight',
  mixins: [flightStatusMixin],
  height: 16,
  props: {
    value: { type: String, default: '' },
    field: { type: Object, required: true },
    row: { type: Object, default: null },
  },
}
</script>
