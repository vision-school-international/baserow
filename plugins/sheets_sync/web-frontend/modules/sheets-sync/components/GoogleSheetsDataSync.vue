<template>
  <form @submit.prevent="submit">
    <p class="margin-bottom-2 margin-top-3">
      {{ $t('googleSheetsDataSync.description') }}
    </p>
    <!-- Write only, like PostgreSQLDataSync's password. -->
    <FormGroup
      :error="fieldHasErrors('google_service_account_key')"
      required
      small-label
      :protected-edit="update"
      class="margin-bottom-2"
      @enabled-protected-edit="values.google_service_account_key = ''"
      @disable-protected-edit="values.google_service_account_key = undefined"
    >
      <template #label>{{
        $t('googleSheetsDataSync.serviceAccountKey')
      }}</template>
      <FormTextarea
        v-model="v$.values.google_service_account_key.$model"
        :rows="6"
        :error="fieldHasErrors('google_service_account_key')"
        :disabled="disabled"
        @blur="v$.values.google_service_account_key.$touch()"
      />
      <template #error>
        {{ v$.values.google_service_account_key.$errors[0]?.$message }}
      </template>
    </FormGroup>
    <FormGroup
      v-for="field in [
        { name: 'google_spreadsheet_id', label: 'spreadsheet' },
        { name: 'google_sheet_name', label: 'sheetName' },
        { name: 'google_id_column', label: 'idColumn' },
      ]"
      :key="field.name"
      :error="fieldHasErrors(field.name)"
      required
      small-label
      class="margin-bottom-2"
    >
      <template #label>{{
        $t(`googleSheetsDataSync.${field.label}`)
      }}</template>
      <FormInput
        v-model="v$.values[field.name].$model"
        size="large"
        :error="fieldHasErrors(field.name)"
        :disabled="disabled"
        @blur="v$.values[field.name].$touch()"
      />
      <template #error>
        {{ v$.values[field.name].$errors[0]?.$message }}
      </template>
    </FormGroup>
  </form>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { required, requiredIf, helpers } from '@vuelidate/validators'
import form from '@baserow/modules/core/mixins/form'

// Same shape as core's PostgreSQLDataSync.vue.
export default {
  name: 'GoogleSheetsDataSync',
  mixins: [form],
  props: {
    update: {
      type: Boolean,
      required: false,
      default: false,
    },
    disabled: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  setup() {
    return { v$: useVuelidate({ $lazy: true }) }
  },
  data() {
    return {
      allowedValues: [
        'google_service_account_key',
        'google_spreadsheet_id',
        'google_sheet_name',
        'google_id_column',
      ],
      values: {
        // If `undefined`, it's left out of the update request and kept.
        google_service_account_key: this.update ? undefined : '',
        google_spreadsheet_id: '',
        google_sheet_name: 'Sheet1',
        google_id_column: 'ID',
      },
    }
  },
  validations() {
    const requiredField = helpers.withMessage(
      this.$t('error.requiredField'),
      required
    )
    return {
      values: {
        google_service_account_key: {
          required: helpers.withMessage(
            this.$t('error.requiredField'),
            requiredIf(
              () => this.values.google_service_account_key !== undefined
            )
          ),
        },
        google_spreadsheet_id: { required: requiredField },
        google_sheet_name: { required: requiredField },
        google_id_column: { required: requiredField },
      },
    }
  },
}
</script>
