<template>
  <div class="control__elements">
    <div v-if="!value" class="flight-tracker__empty">
      {{ $t('flightTracker.noData') }}
    </div>
    <div v-else-if="value.error">{{ trackerText }}</div>
    <dl v-else class="flight-tracker__details">
      <template v-for="line in lines" :key="line.label">
        <dt>{{ line.label }}</dt>
        <dd>{{ line.value }}</dd>
      </template>
    </dl>
  </div>
</template>

<script>
import rowEditField from '@baserow/modules/database/mixins/rowEditField'
import trackerCellMixin from '../trackerCellMixin'

const join = (...parts) => parts.filter(Boolean).join(' · ')

/** Scheduled, then the latest known time if it differs: actual, else estimated. */
const when = (place) => {
  const latest = place.actual || place.estimated
  return latest && latest !== place.scheduled
    ? `${place.scheduled || ''} → ${latest}`
    : place.scheduled || ''
}

/** Every part of the cell's JSON a person needs, read only. */
export default {
  name: 'RowEditFieldFlightTracker',
  mixins: [rowEditField, trackerCellMixin],
  computed: {
    lines() {
      const v = this.value
      const t = (key) => this.$t(`flightTracker.${key}`)
      const dep = v.departure || {}
      const arr = v.arrival || {}
      const place = (p) =>
        join(
          p.airport_iata && `${p.airport_iata} ${p.airport_name || ''}`.trim(),
          p.terminal && `${t('terminal')} ${p.terminal}`,
          p.gate && `${t('gate')} ${p.gate}`
        )
      const delay = (p) =>
        p.delay_minutes > 0
          ? this.$t('flightTracker.delay', { minutes: p.delay_minutes })
          : ''
      return [
        {
          label: t('statusLabel'),
          value: v.status
            ? this.$t(`flightTracker.status.${v.status}`, v.status)
            : '',
        },
        { label: t('airline'), value: join(v.airline_name, v.flight_iata) },
        { label: t('from'), value: place(dep) },
        { label: t('departs'), value: join(when(dep), delay(dep)) },
        { label: t('to'), value: place(arr) },
        { label: t('arrives'), value: join(when(arr), delay(arr)) },
        {
          label: t('baggage'),
          value: arr.baggage || '',
        },
        {
          label: t('aircraft'),
          value: join(v.aircraft_icao, v.aircraft_registration),
        },
      ].filter((line) => line.value)
    },
  },
}
</script>
