<template>
  <li v-if="available" class="context__menu-item">
    <a
      class="context__menu-item-link"
      :class="{ 'context__menu-item-link--loading': loading }"
      @click.prevent="open"
    >
      <i class="context__menu-item-icon iconoir-magic-wand"></i>
      {{ $t('aiTables.transformCells') }}
    </a>
  </li>
</template>

<script>
import { getEnabledModelsForAIProviderFeature } from '@baserow/modules/core/aiProviderModelFeatureTypes'
import { notifyIf } from '@baserow/modules/core/utils/error'
import { TRANSFORM_CELLS_EVENT } from './TransformCellsModal.vue'

// The backend's TRANSFORMABLE_FIELD_TYPES (job_types.py).
const TRANSFORMABLE_FIELD_TYPES = ['text', 'long_text']

/**
 * A `gridSelectionContextItem`: shown for a selection with a writable text column.
 * It stays shown when no model is enabled, and the modal explains why.
 */
export default {
  name: 'TransformCellsContextItem',
  props: {
    fields: { type: Array, required: true },
    getRows: { type: Function, required: true },
    table: { type: Object, required: true },
    view: { type: Object, required: true },
    database: { type: Object, required: true },
    storePrefix: { type: String, required: true },
    readOnly: { type: Boolean, required: true },
  },
  emits: ['click'],
  data() {
    return { loading: false }
  },
  computed: {
    transformableFields() {
      return this.fields.filter(
        (field) =>
          TRANSFORMABLE_FIELD_TYPES.includes(field.type) &&
          this.$registry.get('field', field.type).canWriteFieldValues(field)
      )
    },
    available() {
      // The same gates as the grid's delete rows item (GridView.vue).
      return (
        this.transformableFields.length > 0 &&
        !this.readOnly &&
        (!this.table.data_sync || this.table.data_sync.two_way_sync) &&
        this.$hasPermission(
          'database.table.update_row',
          this.table,
          this.database.workspace.id
        )
      )
    },
  },
  methods: {
    async open() {
      if (this.loading) {
        return
      }
      this.loading = true
      try {
        const workspace = this.$store.getters['workspace/get'](
          this.database.workspace.id
        )
        const enabled = Object.values(
          getEnabledModelsForAIProviderFeature(workspace, 'ai_fields')
        ).some((models) => models.length > 0)
        const rows = enabled ? await this.getRows() : []
        // The modal is in the app layout; this item unmounts with the selection.
        this.$bus.$emit(TRANSFORM_CELLS_EVENT, {
          fields: this.transformableFields,
          rowIds: rows.map((row) => row.id),
          database: this.database,
          workspace,
          enabled,
        })
        this.$emit('click')
      } catch (error) {
        notifyIf(error, 'row')
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
