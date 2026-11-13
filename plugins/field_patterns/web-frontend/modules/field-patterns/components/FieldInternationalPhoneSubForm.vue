<template>
  <FormGroup
    small-label
    :label="$t('fieldPatterns.defaultCountry')"
    :help-icon-tooltip="$t('fieldPatterns.defaultCountryHelp')"
  >
    <Dropdown
      v-model="values.phone_default_country"
      class="dropdown--floating"
      :fixed-items="true"
    >
      <DropdownItem
        v-for="country in countries"
        :key="country.value"
        :name="country.name"
        :value="country.value"
      ></DropdownItem>
    </Dropdown>
  </FormGroup>
</template>

<script>
import { getCountries } from 'libphonenumber-js'
import form from '@baserow/modules/core/mixins/form'
import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'

export default {
  name: 'FieldInternationalPhoneSubForm',
  mixins: [form, fieldSubForm],
  data() {
    return {
      allowedValues: ['phone_default_country'],
      values: {
        phone_default_country: '',
      },
    }
  },
  computed: {
    countries() {
      const names = new Intl.DisplayNames([this.$i18n.locale, 'en'], {
        type: 'region',
      })
      const countries = getCountries()
        .map((code) => ({ value: code, name: `${names.of(code)} (${code})` }))
        .sort((a, b) => a.name.localeCompare(b.name))
      return [
        { value: '', name: this.$t('fieldPatterns.noDefaultCountry') },
        ...countries,
      ]
    },
  },
}
</script>
