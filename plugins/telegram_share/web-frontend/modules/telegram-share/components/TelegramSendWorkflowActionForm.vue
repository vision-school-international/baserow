<template>
  <!-- The open URL form's layout classes: same rows, no styles of its own. -->
  <div class="open-url-workflow-action-form">
    <div class="open-url-workflow-action-form__row">
      <div class="open-url-workflow-action-form__label">
        {{ $t('telegramShare.recipient') }}
      </div>
      <div class="open-url-workflow-action-form__control">
        <DatabaseFormulaInput
          :value="values.recipient"
          :data-providers-allowed="['fields', 'previous_action']"
          :placeholder="$t('telegramShare.recipientPlaceholder')"
          @input="values.recipient = $event"
          @update:invalid="recipientInvalid = $event"
        />
      </div>
    </div>
    <div class="open-url-workflow-action-form__row">
      <div class="open-url-workflow-action-form__label">
        {{ $t('telegramShare.message') }}
      </div>
      <div class="open-url-workflow-action-form__control">
        <DatabaseFormulaInput
          :value="values.message"
          :data-providers-allowed="['fields', 'previous_action']"
          :placeholder="$t('telegramShare.messagePlaceholder')"
          @input="values.message = $event"
          @update:invalid="messageInvalid = $event"
        />
      </div>
    </div>
    <div class="open-url-workflow-action-form__row">
      <div class="open-url-workflow-action-form__label">
        {{ $t('telegramShare.form') }}
      </div>
      <div class="open-url-workflow-action-form__control">
        <Dropdown v-model="values.form_view_id" :fixed-items="true">
          <DropdownItem
            :name="$t('telegramShare.noForm')"
            :value="null"
          ></DropdownItem>
          <DropdownItem
            v-for="view in forms"
            :key="view.id"
            :name="view.name"
            :value="view.id"
          ></DropdownItem>
        </Dropdown>
      </div>
    </div>
    <template v-if="values.form_view_id">
      <Checkbox v-model="values.prefill">{{
        $t('telegramShare.prefill')
      }}</Checkbox>
      <Alert v-if="selectedForm && !selectedForm.public" type="warning">
        {{ $t('telegramShare.formNotPublic') }}
      </Alert>
    </template>
  </div>
</template>

<script>
import form from '@baserow/modules/core/mixins/form'
import DatabaseFormulaInput from '@baserow/modules/database/components/field/DatabaseFormulaInput'
import ViewService from '@baserow/modules/database/services/view'
import { notifyIf } from '@baserow/modules/core/utils/error'

/**
 * Config form for a `telegram_send` action, like OpenUrlWorkflowActionForm.
 * The form link can only be a form of the button's table: the backend refuses
 * others (telegram_share/workflow_action_types.py).
 */
export default {
  name: 'TelegramSendWorkflowActionForm',
  components: { DatabaseFormulaInput },
  mixins: [form],
  inject: {
    // FieldButtonSubForm's context, which holds the button's table.
    formulaContext: { from: 'databaseFormulaContext', default: null },
  },
  data() {
    return {
      allowedValues: ['recipient', 'message', 'form_view_id', 'prefill'],
      values: {
        recipient: { formula: '', mode: 'simple' },
        message: { formula: '', mode: 'simple' },
        form_view_id: null,
        prefill: false,
      },
      recipientInvalid: false,
      messageInvalid: false,
      forms: [],
    }
  },
  computed: {
    selectedForm() {
      return this.forms.find((view) => view.id === this.values.form_view_id)
    },
  },
  /**
   * Fetched rather than read from the store: the store holds the open table's
   * views, and a linked row's modal edits a button of another table.
   */
  async mounted() {
    const tableId = this.formulaContext?.table?.id
    if (!tableId) {
      return
    }
    try {
      const { data } = await ViewService(this.$client).fetchAll(
        tableId,
        false,
        false,
        false,
        false,
        false,
        null,
        'form'
      )
      this.forms = data
    } catch (error) {
      notifyIf(error, 'view')
    }
  },
  methods: {
    /** Like the open URL form: an unparseable formula blocks the save. */
    isFormValid(deep = false) {
      return (
        !this.recipientInvalid &&
        !this.messageInvalid &&
        form.methods.isFormValid.call(this, deep)
      )
    },
  },
}
</script>
