<template>
  <div>
    <FormGroup
      small-label
      class="margin-bottom-2"
      :label="$t('flightTracker.codeField')"
      :helper-text="$t('flightTracker.codeFieldHelp')"
      :error="v$.values.flight_code_field_id.$error"
    >
      <Dropdown
        v-model="v$.values.flight_code_field_id.$model"
        class="dropdown--floating"
        :fixed-items="true"
      >
        <DropdownItem
          v-for="codeField in codeFields"
          :key="codeField.id"
          :name="codeField.name"
          :value="codeField.id"
        />
      </Dropdown>
      <template #error>{{ $t('flightTracker.codeFieldRequired') }}</template>
    </FormGroup>
    <FormGroup
      small-label
      class="margin-bottom-2"
      :label="$t('flightTracker.refresh')"
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
    <FormGroup
      small-label
      :label="$t('flightTracker.interval')"
      :helper-text="
        $t(
          values.flight_refresh === 'schedule'
            ? 'flightTracker.intervalScheduleHelp'
            : 'flightTracker.intervalViewHelp'
        )
      "
      :error="v$.values.flight_interval_minutes.$error"
    >
      <FormInput
        v-model="v$.values.flight_interval_minutes.$model"
        type="number"
        :min="MIN"
        :max="MAX"
        :error="v$.values.flight_interval_minutes.$error"
        @blur="v$.values.flight_interval_minutes.$touch()"
      />
      <template #error>
        {{ $t('flightTracker.intervalInvalid', { min: MIN, max: MAX }) }}
      </template>
    </FormGroup>
  </div>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { between, integer, required } from '@vuelidate/validators'
import form from '@baserow/modules/core/mixins/form'
import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'

// flight_tracker/models.py MIN_INTERVAL_MINUTES and MAX_INTERVAL_MINUTES.
const MIN = 5
const MAX = 7 * 24 * 60
// flight_tracker/field_types.py CODE_FIELD_TYPES.
const CODE_FIELD_TYPES = ['text', 'long_text', 'flight', 'pattern_text']

export default {
  name: 'FieldFlightTrackerSubForm',
  mixins: [form, fieldSubForm],
  setup() {
    return { v$: useVuelidate({ $lazy: true }) }
  },
  data() {
    return {
      MIN,
      MAX,
      allowedValues: [
        'flight_code_field_id',
        'flight_refresh',
        'flight_interval_minutes',
      ],
      values: {
        flight_code_field_id: null,
        flight_refresh: 'view',
        flight_interval_minutes: 30,
      },
    }
  },
  computed: {
    codeFields() {
      return (this.allFieldsInTable || []).filter((field) =>
        CODE_FIELD_TYPES.includes(field.type)
      )
    },
  },
  methods: {
    getFormValues() {
      const values = form.methods.getFormValues.call(this)
      // The number input gives a string.
      values.flight_interval_minutes = Number(values.flight_interval_minutes)
      return values
    },
  },
  validations() {
    return {
      values: {
        flight_code_field_id: { required },
        flight_interval_minutes: {
          required,
          integer,
          between: between(MIN, MAX),
        },
      },
    }
  },
}
</script>
