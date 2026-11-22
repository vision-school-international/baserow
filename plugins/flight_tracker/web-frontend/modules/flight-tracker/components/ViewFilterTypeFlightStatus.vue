<template>
  <Dropdown
    :value="filter.value"
    :show-search="false"
    :fixed-items="true"
    :disabled="readOnly"
    class="filters__value-dropdown"
    @input="$emit('input', $event)"
  >
    <DropdownItem
      v-for="option in options"
      :key="option"
      :name="$t(`flightTracker.filter.${option}`)"
      :value="option"
    ></DropdownItem>
  </Dropdown>
</template>

<script>
// flight_tracker/view_filters.py; like core's ViewFilterTypeFileTypeDropdown.
export const FLIGHT_FILTER_VALUES = [
  'scheduled',
  'en-route',
  'landed',
  'not_found',
  'invalid_flight_number',
  'none',
]

export default {
  name: 'ViewFilterTypeFlightStatus',
  props: {
    filter: { type: Object, required: true },
    fields: { type: Array, required: true },
    readOnly: { type: Boolean, required: true },
  },
  emits: ['input'],
  data() {
    return { options: FLIGHT_FILTER_VALUES }
  },
}
</script>
