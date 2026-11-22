<template>
  <FormGroup
    small-label
    :label="$t('flightTracker.refresh')"
    :helper-text="$t('flightTracker.refreshHelp')"
  >
    <Dropdown v-model="values.flight_refresh" :fixed-items="true">
      <DropdownItem
        :name="$t('flightTracker.refreshView')"
        value="view"
      ></DropdownItem>
      <DropdownItem
        :name="$t('flightTracker.refreshSchedule')"
        value="schedule"
      ></DropdownItem>
    </Dropdown>
  </FormGroup>
</template>

<script>
import form from '@baserow/modules/core/mixins/form'
import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'

// Same as field_patterns' FieldTimeOfDaySubForm.
export default {
  name: 'FieldFlightSubForm',
  mixins: [form, fieldSubForm],
  data() {
    return {
      allowedValues: ['flight_refresh'],
      values: {
        flight_refresh: 'view',
      },
    }
  },
}
</script>
