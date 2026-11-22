<template>
  <FormGroup :error="touched && !valid">
    <FormInput
      ref="input"
      v-model="copy"
      size="large"
      :placeholder="$t('flightTracker.placeholder')"
      :error="touched && !valid"
      :disabled="readOnly"
      @keyup.enter="$refs.input.blur()"
      @focus="select()"
      @blur="unselect()"
    />
    <dl v-if="flightStatus" class="flight-tracker__details">
      <template v-for="line in lines" :key="line.label">
        <dt>{{ line.label }}</dt>
        <dd>{{ line.value }}</dd>
      </template>
    </dl>

    <template #error>
      <span v-show="touched && !valid">
        {{ error }}
      </span>
    </template>
  </FormGroup>
</template>

<script>
import rowEditField from '@baserow/modules/database/mixins/rowEditField'
import rowEditFieldInput from '@baserow/modules/database/mixins/rowEditFieldInput'
import flightStatusMixin from '../flightStatusMixin'

const place = (iata, terminal, gate, extra = []) =>
  [iata, terminal && `T${terminal}`, gate && `Gate ${gate}`, ...extra]
    .filter(Boolean)
    .join(' · ')

// Scheduled, then the latest known time if it differs: actual, else estimated.
const when = (scheduled, estimated, actual) => {
  const latest = actual || estimated
  return latest && latest !== scheduled
    ? `${scheduled} → ${latest}`
    : scheduled || ''
}

/** Core's RowEditFieldText, with the flight's details under it. */
export default {
  name: 'RowEditFieldFlight',
  mixins: [rowEditField, rowEditFieldInput, flightStatusMixin],
  computed: {
    lines() {
      const s = this.flightStatus
      const t = (key) => this.$t(`flightTracker.${key}`)
      const text = this.flightText
      const baggage = s.arr_baggage ? [`${t('baggage')} ${s.arr_baggage}`] : []
      return [
        {
          label: t('statusLabel'),
          value: [text.state, text.delay].filter(Boolean).join(' · '),
        },
        {
          label: t('from'),
          value: place(s.dep_iata, s.dep_terminal, s.dep_gate),
        },
        {
          label: t('departs'),
          value: when(s.dep_time, s.dep_estimated, s.dep_actual),
        },
        {
          label: t('to'),
          value: place(s.arr_iata, s.arr_terminal, s.arr_gate, baggage),
        },
        {
          label: t('arrives'),
          value: when(s.arr_time, s.arr_estimated, s.arr_actual),
        },
      ].filter((line) => line.value)
    },
  },
  methods: {
    // As the backend stores it (flight_tracker/flight.py clean_flight).
    beforeSave(value) {
      return (value || '').replace(/\s+/g, '').toUpperCase()
    },
  },
}
</script>
