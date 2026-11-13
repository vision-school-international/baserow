<template>
  <FormGroup :error="touched && !valid">
    <FormInput
      ref="input"
      v-model="copy"
      size="large"
      :type="inputType"
      :error="touched && !valid"
      :disabled="readOnly"
      @keyup.enter="$refs.input.blur()"
      @focus="select()"
      @blur="unselect()"
    />

    <template #error>
      <span v-show="touched && !valid">
        {{ error }}
      </span>
    </template>
  </FormGroup>
</template>

<script>
import debounce from 'lodash/debounce'
import rowEditField from '@baserow/modules/database/mixins/rowEditField'
import rowEditFieldInput from '@baserow/modules/database/mixins/rowEditFieldInput'
import PatternTextService from '../services/patternText'

// How long typing has to pause before the value is checked.
const CHECK_DELAY = 400

/**
 * The form input of a pattern text field (RowEditFieldText). While the respondent
 * types, the backend checks the value against the field's pattern, so the error
 * shows before the form is submitted.
 */
export default {
  mixins: [rowEditField, rowEditFieldInput],
  props: {
    slug: {
      type: String,
      required: false,
      default: null,
    },
  },
  data() {
    return {
      // The backend's error for `checkedValue`, or null when it matched.
      checkError: null,
      checkedValue: null,
    }
  },
  computed: {
    inputType() {
      return 'text'
    },
  },
  watch: {
    copy(value) {
      this.debouncedCheck(value)
    },
  },
  created() {
    this.debouncedCheck = debounce(this.check, CHECK_DELAY)
  },
  beforeUnmount() {
    this.debouncedCheck.cancel()
  },
  methods: {
    async check(value) {
      if (!this.slug || value === null || value === '') {
        return
      }
      try {
        const { data } = await PatternTextService(this.$client).checkFormValue(
          this.slug,
          this.field.id,
          value,
          this.$store.getters['page/view/public/getAuthToken']
        )
        // An older answer that arrives late must not replace a newer one.
        if (value !== this.copy) {
          return
        }
        this.checkError = data.valid ? null : data.error
        this.checkedValue = value
        if (this.checkError) {
          this.touch()
        }
      } catch {
        // The submit checks the value again, and shows its error.
      }
    },
    unselect() {
      this.debouncedCheck.flush()
      rowEditFieldInput.methods.unselect.call(this)
    },
    getValidationError(value) {
      const error = rowEditField.methods.getValidationError.call(this, value)
      if (error !== null) {
        return error
      }
      return value === this.checkedValue ? this.checkError : null
    },
  },
}
</script>
