<template>
  <div class="context__form-container">
    <SelectAIModelForm
      :default-values="defaultValues"
      :database="database"
      feature-type="ai_fields"
      @ai-type-changed="onAITypeChanged"
    ></SelectAIModelForm>

    <FormGroup
      small-label
      required
      :label="$t('aiTables.prompt')"
      :help-icon-tooltip="$t('aiTables.promptHelp')"
      :error="v$.values.ai_prompt.formula.$error || promptInvalid"
    >
      <FormulaInputField
        :value="values.ai_prompt.formula"
        :mode="values.ai_prompt.mode"
        :nodes-hierarchy="nodesHierarchy"
        :placeholder="$t('aiTables.promptPlaceholder')"
        :validation-context="{ dataProviderRegistry: dataProviders }"
        @input="setFormula"
        @update:mode="setMode"
        @update:invalid="promptInvalid = $event"
      />
      <template #error>
        {{
          promptInvalid
            ? $t('aiTables.promptInvalid')
            : $t('error.requiredField')
        }}
      </template>
    </FormGroup>

    <FormGroup
      v-if="filesSupported"
      small-label
      :label="$t('aiTables.fileField')"
      :help-icon-tooltip="$t('aiTables.fileFieldHelp')"
    >
      <Dropdown
        v-model="values.ai_file_field_id"
        class="dropdown--floating"
        :fixed-items="true"
        :show-search="false"
      >
        <DropdownItem :name="$t('aiTables.noFileField')" :value="null" />
        <DropdownItem
          v-for="fileField in fileFields"
          :key="fileField.id"
          :name="fileField.name"
          :value="fileField.id"
        />
      </Dropdown>
    </FormGroup>

    <FormGroup
      small-label
      :label="$t('aiTables.autoUpdate')"
      :help-icon-tooltip="$t('aiTables.autoUpdateHelp')"
    >
      <Checkbox v-model="values.ai_auto_update">
        {{ $t('aiTables.autoUpdateLabel') }}
      </Checkbox>
    </FormGroup>
  </div>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { required } from '@vuelidate/validators'
import form from '@baserow/modules/core/mixins/form'
import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'
import FormulaInputField from '@baserow/modules/core/components/formula/FormulaInputField'
import SelectAIModelForm from '@baserow/modules/core/components/ai/SelectAIModelForm'
import { buildFormulaFunctionNodes } from '@baserow/modules/core/formula'
import { getDataNodesFromDataProvider } from '@baserow/modules/core/utils/dataProviders'

export default {
  name: 'AIPromptTextFieldSubForm',
  components: { SelectAIModelForm, FormulaInputField },
  mixins: [form, fieldSubForm],
  setup() {
    return { v$: useVuelidate({ $lazy: true }) }
  },
  data() {
    return {
      allowedValues: ['ai_prompt', 'ai_file_field_id', 'ai_auto_update'],
      values: {
        ai_prompt: { formula: '', mode: 'simple' },
        ai_file_field_id: null,
        ai_auto_update: false,
      },
      filesSupported: false,
      promptInvalid: false,
    }
  },
  computed: {
    dataProviders() {
      return [this.$registry.get('databaseDataProvider', 'fields')]
    },
    nodesHierarchy() {
      // The prompt can't read the field's own cell.
      const context = {
        fields: this.allFieldsInTable.filter(
          (field) => field.id !== this.defaultValues.id
        ),
      }
      const hierarchy = []
      const dataNodes = getDataNodesFromDataProvider(
        this.dataProviders,
        context
      )
      if (dataNodes.length > 0) {
        hierarchy.push({
          name: this.$t('aiTables.fields'),
          type: 'data',
          icon: 'iconoir-database',
          nodes: dataNodes,
        })
      }
      hierarchy.push(...buildFormulaFunctionNodes(this))
      return hierarchy
    },
    fileFields() {
      return this.allFieldsInTable.filter((field) =>
        this.$registry.get('field', field.type).canRepresentFiles(field)
      )
    },
  },
  methods: {
    // The editor only emits valid formulas; an invalid one must block saving
    // instead of silently keeping the previous prompt.
    isFormValid(deep = false) {
      return !this.promptInvalid && form.methods.isFormValid.call(this, deep)
    },
    setFormula(formula) {
      this.values.ai_prompt = { ...this.values.ai_prompt, formula }
      this.v$.values.ai_prompt.formula.$touch()
    },
    setMode(mode) {
      this.values.ai_prompt = { ...this.values.ai_prompt, mode }
    },
    onAITypeChanged(aiType) {
      const modelType = aiType
        ? this.$registry.getAll('generativeAIModel')[aiType]
        : null
      this.filesSupported = Boolean(modelType?.canPromptWithFiles())
      if (!this.filesSupported) {
        this.values.ai_file_field_id = null
      }
    },
  },
  validations() {
    return {
      values: {
        ai_prompt: { formula: { required } },
      },
    }
  },
}
</script>
