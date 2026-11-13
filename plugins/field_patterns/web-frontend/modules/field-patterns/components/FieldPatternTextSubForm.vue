<template>
  <div>
    <FormGroup
      required
      small-label
      :label="$t('fieldPatterns.pattern')"
      :help-icon-tooltip="$t('fieldPatterns.patternHelp')"
      :error="fieldHasErrors('pattern')"
      class="margin-bottom-2"
    >
      <FormInput
        v-model="v$.values.pattern.$model"
        :placeholder="$t('fieldPatterns.patternPlaceholder')"
        :error="fieldHasErrors('pattern')"
        @blur="v$.values.pattern.$touch"
      ></FormInput>
      <template #error>{{ v$.values.pattern.$errors[0]?.$message }}</template>
    </FormGroup>
    <FormGroup
      small-label
      :label="$t('fieldPatterns.errorMessage')"
      :error="fieldHasErrors('pattern_error_message')"
      class="margin-bottom-2"
    >
      <FormInput
        v-model="v$.values.pattern_error_message.$model"
        :placeholder="$t('fieldPatterns.errorMessagePlaceholder')"
        :error="fieldHasErrors('pattern_error_message')"
        @blur="v$.values.pattern_error_message.$touch"
      ></FormInput>
      <template #error>{{
        v$.values.pattern_error_message.$errors[0]?.$message
      }}</template>
    </FormGroup>
    <FormGroup
      small-label
      :label="$t('fieldPatterns.case')"
      class="margin-bottom-2"
    >
      <Dropdown
        v-model="values.pattern_case"
        class="dropdown--floating"
        :show-search="false"
        :fixed-items="true"
      >
        <DropdownItem
          v-for="option in caseOptions"
          :key="option.value"
          :name="option.name"
          :value="option.value"
        ></DropdownItem>
      </Dropdown>
    </FormGroup>
    <FormGroup small-label :label="$t('fieldPatterns.trim')">
      <Checkbox v-model="values.pattern_trim">{{
        $t('fieldPatterns.trimLabel')
      }}</Checkbox>
    </FormGroup>
  </div>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { required, maxLength, helpers } from '@vuelidate/validators'
import form from '@baserow/modules/core/mixins/form'
import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'

// The backend's limits (field_patterns/models.py). The backend also checks that the
// pattern compiles; the browser's RegExp syntax differs, so it isn't checked here.
const PATTERN_MAX_LENGTH = 500
const ERROR_MESSAGE_MAX_LENGTH = 255

export default {
  name: 'FieldPatternTextSubForm',
  mixins: [form, fieldSubForm],
  setup() {
    return { v$: useVuelidate({ $lazy: true }) }
  },
  data() {
    return {
      allowedValues: [
        'pattern',
        'pattern_error_message',
        'pattern_trim',
        'pattern_case',
      ],
      values: {
        pattern: '',
        pattern_error_message: '',
        pattern_trim: true,
        pattern_case: 'none',
      },
    }
  },
  computed: {
    caseOptions() {
      return [
        { value: 'none', name: this.$t('fieldPatterns.caseNone') },
        { value: 'lower', name: this.$t('fieldPatterns.caseLower') },
        { value: 'upper', name: this.$t('fieldPatterns.caseUpper') },
      ]
    },
  },
  validations() {
    return {
      values: {
        pattern: {
          required: helpers.withMessage(
            this.$t('error.requiredField'),
            required
          ),
          maxLength: helpers.withMessage(
            this.$t('error.maxLength', { max: PATTERN_MAX_LENGTH }),
            maxLength(PATTERN_MAX_LENGTH)
          ),
        },
        pattern_error_message: {
          maxLength: helpers.withMessage(
            this.$t('error.maxLength', { max: ERROR_MESSAGE_MAX_LENGTH }),
            maxLength(ERROR_MESSAGE_MAX_LENGTH)
          ),
        },
      },
    }
  },
}
</script>
