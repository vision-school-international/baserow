<template>
  <div>
    <AIPromptTextFieldSubForm
      :default-values="defaultValues"
      :table="table"
      :field-type="fieldType"
      :view="view"
      :primary="primary"
      :all-fields-in-table="allFieldsInTable"
      :database="database"
    />
    <div v-if="loading" class="loading"></div>
    <FormGroup
      v-else
      small-label
      required
      :label="$t('aiTables.options')"
      :help-icon-tooltip="$t('aiTables.optionsHelp')"
    >
      <FieldSelectOptions
        ref="selectOptions"
        v-model="values.select_options"
      ></FieldSelectOptions>
    </FormGroup>
  </div>
</template>

<script>
import fieldOptionsSubForm from '@baserow/modules/database/mixins/fieldOptionsSubForm'
import AIPromptTextFieldSubForm from './AIPromptTextFieldSubForm.vue'

// The options the model chooses from; there is no default option.
export default {
  name: 'AIPromptChoiceFieldSubForm',
  components: { AIPromptTextFieldSubForm },
  mixins: [fieldOptionsSubForm],
  methods: {
    // The mixin only checks the options; the prompt form must be valid too.
    isFormValid(deep = false) {
      const optionsValid = fieldOptionsSubForm.methods.isFormValid.call(this)
      return optionsValid && this.areChildFormsValid(deep)
    },
  },
}
</script>
