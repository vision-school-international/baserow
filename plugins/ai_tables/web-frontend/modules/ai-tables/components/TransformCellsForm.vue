<template>
  <form @submit.prevent="submit">
    <FormGroup
      small-label
      required
      :label="$t('aiTables.instruction')"
      :help-icon-tooltip="$t('aiTables.instructionHelp')"
      :error="fieldHasErrors('instruction')"
    >
      <FormTextarea
        ref="instruction"
        v-model="v$.values.instruction.$model"
        :rows="3"
        :placeholder="$t('aiTables.instructionPlaceholder')"
        :error="fieldHasErrors('instruction')"
        @blur="v$.values.instruction.$touch"
      />
      <template #error>{{
        v$.values.instruction.$errors[0]?.$message
      }}</template>
    </FormGroup>
    <SelectAIModelForm :database="database" feature-type="ai_fields" />
    <slot></slot>
  </form>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { required, maxLength, helpers } from '@vuelidate/validators'
import form from '@baserow/modules/core/mixins/form'
import SelectAIModelForm from '@baserow/modules/core/components/ai/SelectAIModelForm'

// Same limit as the job's request serializer (job_types.py).
const INSTRUCTION_MAX_LENGTH = 2000

export default {
  name: 'TransformCellsForm',
  components: { SelectAIModelForm },
  mixins: [form],
  props: {
    database: { type: Object, required: true },
  },
  setup() {
    return { v$: useVuelidate({ $lazy: true }) }
  },
  data() {
    return {
      values: { instruction: '' },
    }
  },
  mounted() {
    this.$refs.instruction.focus()
  },
  validations() {
    return {
      values: {
        instruction: {
          required: helpers.withMessage(
            this.$t('error.requiredField'),
            required
          ),
          maxLength: helpers.withMessage(
            this.$t('error.maxLength', { max: INSTRUCTION_MAX_LENGTH }),
            maxLength(INSTRUCTION_MAX_LENGTH)
          ),
        },
      },
    }
  },
}
</script>
