<template>
  <Modal ref="modal" :small="true">
    <template v-if="field">
      <h2 class="box__title">
        {{ $t('aiTables.transformTitle', { name: field.name }) }}
      </h2>
      <p>
        {{ $t('aiTables.transformDescription', { count: rowIds.length }) }}
      </p>
      <Error :error="error"></Error>
      <TransformCellsForm :database="database" @submitted="transform">
        <div class="actions">
          <ul class="action__links">
            <li>
              <a @click.prevent="hide()">{{ $t('aiTables.close') }}</a>
            </li>
          </ul>
          <Button type="primary" :loading="loading" :disabled="loading">
            {{ $t('aiTables.transform') }}
          </Button>
        </div>
      </TransformCellsForm>
    </template>
  </Modal>
</template>

<script>
import error from '@baserow/modules/core/mixins/error'
import modal from '@baserow/modules/core/mixins/modal'
import JobService from '@baserow/modules/core/services/job'
import TransformCellsForm from './TransformCellsForm.vue'

export const TRANSFORM_CELLS_EVENT = 'ai-tables-transform-cells'

/**
 * Mounted in the app layout by AITablesPlugin, and opened through the bus by the
 * grid's cell-selection menu, whose items unmount once the selection is cleared.
 */
export default {
  name: 'TransformCellsModal',
  components: { TransformCellsForm },
  mixins: [error, modal],
  data() {
    return {
      field: null,
      rowIds: [],
      database: null,
      loading: false,
    }
  },
  mounted() {
    this.$bus.$on(TRANSFORM_CELLS_EVENT, this.open)
  },
  beforeUnmount() {
    this.$bus.$off(TRANSFORM_CELLS_EVENT, this.open)
  },
  methods: {
    open({ field, rowIds, database }) {
      this.field = field
      this.rowIds = rowIds
      this.database = database
      this.hideError()
      this.show()
    },
    async transform(values) {
      this.hideError()
      this.loading = true
      try {
        const { data } = await JobService(this.$client).create(
          'transform_ai_cells',
          { ...values, field_id: this.field.id, row_ids: this.rowIds }
        )
        // The job store polls it; the cells update through the realtime events.
        await this.$store.dispatch('job/create', data)
        this.hide()
      } catch (err) {
        this.handleError(err)
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
