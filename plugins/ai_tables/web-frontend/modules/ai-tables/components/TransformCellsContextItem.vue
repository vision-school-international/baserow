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

export default {
  name: 'TransformCellsContextItem',
  props: {
    field: { type: Object, required: true },
    getRows: { type: Function, required: true },
    storePrefix: { type: String, required: true },
    database: { type: Object, required: true },
  },
  emits: ['click'],
  data() {
    return { loading: false }
  },
  computed: {
    available() {
      const workspace = this.$store.getters['workspace/get'](
        this.database.workspace.id
      )
      const table = this.database.tables?.find(
        (t) => t.id === this.field.table_id
      )
      return (
        Boolean(table) &&
        !this.field.read_only &&
        this.$hasPermission(
          'database.table.update_row',
          table,
          this.database.workspace.id
        ) &&
        Object.values(
          getEnabledModelsForAIProviderFeature(workspace, 'ai_fields')
        ).some((models) => models.length > 0)
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
        const rows = await this.getRows()
        // The modal is in the app layout; this item unmounts with the selection.
        this.$bus.$emit(TRANSFORM_CELLS_EVENT, {
          field: this.field,
          rowIds: rows.map((row) => row.id),
          database: this.database,
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
