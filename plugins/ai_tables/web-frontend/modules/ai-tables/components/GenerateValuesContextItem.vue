<template>
  <li v-if="isAIPromptField" class="context__menu-item">
    <a class="context__menu-item-link" @click.prevent="open">
      <i class="context__menu-item-icon iconoir-magic-wand"></i>
      {{ $t('aiTables.generateValues') }}
    </a>
    <GenerateValuesModal ref="modal" :field="field" :view="view" />
  </li>
</template>

<script>
import GenerateValuesModal from './GenerateValuesModal.vue'
import { AI_PROMPT_FIELD_TYPES } from '../constants'

export default {
  name: 'GenerateValuesContextItem',
  components: { GenerateValuesModal },
  props: {
    field: { type: Object, required: true },
    view: { type: Object, required: false, default: null },
    table: { type: Object, required: true },
    database: { type: Object, required: true },
  },
  emits: ['hide-context'],
  computed: {
    isAIPromptField() {
      return (
        AI_PROMPT_FIELD_TYPES.includes(this.field.type) &&
        this.$hasPermission(
          'database.table.update_row',
          this.table,
          this.database.workspace.id
        )
      )
    },
  },
  methods: {
    open() {
      this.$refs.modal.show()
      this.$emit('hide-context')
    },
  },
}
</script>
