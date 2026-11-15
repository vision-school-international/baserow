<template>
  <FormGroup small-label :label="$t('fieldPatterns.timeFormat')">
    <Dropdown v-model="values.time_format" :fixed-items="true">
      <DropdownItem
        :name="$t('fieldPatterns.timeFormat24')"
        value="24"
      ></DropdownItem>
      <DropdownItem
        :name="$t('fieldPatterns.timeFormat12')"
        value="12"
      ></DropdownItem>
    </Dropdown>
  </FormGroup>
</template>

<script>
import form from '@baserow/modules/core/mixins/form'
import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'

// Same as FieldInternationalPhoneSubForm.
export default {
  name: 'FieldTimeOfDaySubForm',
  mixins: [form, fieldSubForm],
  data() {
    return {
      allowedValues: ['time_format'],
      values: {
        time_format: '24',
      },
    }
  },
}
</script>
