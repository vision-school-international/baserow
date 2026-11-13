<template>
  <div>
    <Modal ref="modal" :small="true">
      <template v-if="workspace && !enabled">
        <h2 class="box__title">{{ $t('aiTables.transformCells') }}</h2>
        <p>
          {{
            canConfigure
              ? $t('aiTables.transformNotEnabled')
              : $t('aiTables.transformNotEnabledAskAdmin')
          }}
        </p>
        <div class="actions">
          <ul class="action__links">
            <li>
              <a @click.prevent="hide()">{{ $t('aiTables.close') }}</a>
            </li>
          </ul>
          <Button v-if="canConfigure" type="primary" @click="openSettings">
            {{ $t('aiTables.openAIProviders') }}
          </Button>
        </div>
      </template>
      <template v-else-if="fields.length > 0">
        <h2 class="box__title">{{ $t('aiTables.transformCells') }}</h2>
        <p>{{ $t('aiTables.transformDescription') }}</p>
        <FormGroup
          small-label
          required
          :label="$t('aiTables.columns')"
          class="margin-bottom-2"
        >
          <Checkbox
            v-for="field in fields"
            :key="field.id"
            :model-value="selectedFieldIds.includes(field.id)"
            class="margin-bottom-1"
            @update:model-value="toggleField(field.id, $event)"
            >{{ field.name }}</Checkbox
          >
        </FormGroup>
        <Alert v-if="cellCount > maxCells" type="error">
          {{
            $t('aiTables.transformTooMany', { count: cellCount, max: maxCells })
          }}
        </Alert>
        <p v-else>
          {{ $t('aiTables.transformCount', { count: cellCount }) }}
        </p>
        <Error :error="error"></Error>
        <TransformCellsForm :database="database" @submitted="transform">
          <div class="actions">
            <ul class="action__links">
              <li>
                <a @click.prevent="hide()">{{ $t('aiTables.close') }}</a>
              </li>
            </ul>
            <Button
              type="primary"
              :loading="loading"
              :disabled="loading || cellCount === 0 || cellCount > maxCells"
            >
              {{ $t('aiTables.transform') }}
            </Button>
          </div>
        </TransformCellsForm>
      </template>
    </Modal>
    <!-- Opened by the job type when the AI is done. Nothing is saved before. -->
    <Modal ref="previewModal">
      <template v-if="preview">
        <h2 class="box__title">{{ $t('aiTables.previewTitle') }}</h2>
        <p>{{ $t('aiTables.previewDescription') }}</p>
        <Alert v-if="preview.failed_row_ids?.length" type="warning">
          {{
            $t('aiTables.previewFailed', {
              count: preview.failed_row_ids.length,
            })
          }}
        </Alert>
        <Checkbox
          v-for="proposal in preview.proposals"
          :key="cellKey(proposal)"
          :model-value="kept.includes(cellKey(proposal))"
          class="margin-bottom-2"
          @update:model-value="toggleKept(cellKey(proposal), $event)"
        >
          <strong>{{
            $t('aiTables.previewCell', {
              row: proposal.row_name || proposal.row_id,
              column: proposal.field_name,
            })
          }}</strong>
          <br />
          <del>{{ proposal.old }}</del>
          <br />
          {{ proposal.new }}
        </Checkbox>
        <Error :error="error"></Error>
        <div class="actions">
          <ul class="action__links">
            <li>
              <a @click.prevent="reject">{{ $t('aiTables.rejectAll') }}</a>
            </li>
          </ul>
          <Button
            type="primary"
            :loading="applying"
            :disabled="applying || kept.length === 0"
            @click="apply"
          >
            {{ $t('aiTables.applyChanges', { count: kept.length }) }}
          </Button>
        </div>
      </template>
    </Modal>
    <!-- Outside the Modal, whose content unmounts when it hides. -->
    <WorkspaceSettingsModal
      v-if="workspace && canConfigure"
      ref="workspaceSettingsModal"
      :workspace="workspace"
    ></WorkspaceSettingsModal>
  </div>
</template>

<script>
import error from '@baserow/modules/core/mixins/error'
import modal from '@baserow/modules/core/mixins/modal'
import JobService from '@baserow/modules/core/services/job'
import WorkspaceSettingsModal from '@baserow/modules/core/components/workspace/WorkspaceSettingsModal'
import TransformCellsForm from './TransformCellsForm.vue'

export const TRANSFORM_CELLS_EVENT = 'ai-tables-transform-cells'
export const TRANSFORM_PREVIEW_EVENT = 'ai-tables-transform-preview'

const cellKey = (proposal) => `${proposal.row_id}:${proposal.field_id}`

// The backend's BATCH_ROWS_SIZE_LIMIT default; the job refuses more rows x columns.
const MAX_CELLS = 200

/**
 * Mounted in the app layout by AITablesPlugin, and opened through the bus by the
 * grid's selection menu, whose items unmount once the selection is cleared.
 */
export default {
  name: 'TransformCellsModal',
  components: { TransformCellsForm, WorkspaceSettingsModal },
  mixins: [error, modal],
  data() {
    return {
      fields: [],
      selectedFieldIds: [],
      rowIds: [],
      database: null,
      workspace: null,
      enabled: false,
      loading: false,
      maxCells: MAX_CELLS,
      // The finished job whose proposals are previewed, and the kept ones.
      preview: null,
      kept: [],
      applying: false,
    }
  },
  computed: {
    cellCount() {
      return this.rowIds.length * this.selectedFieldIds.length
    },
    canConfigure() {
      // The same gate as the workspace context's settings modal.
      return (
        this.workspace !== null &&
        this.$hasPermission(
          'workspace.update',
          this.workspace,
          this.workspace.id
        )
      )
    },
  },
  mounted() {
    this.$bus.$on(TRANSFORM_CELLS_EVENT, this.open)
    this.$bus.$on(TRANSFORM_PREVIEW_EVENT, this.openPreview)
  },
  beforeUnmount() {
    this.$bus.$off(TRANSFORM_CELLS_EVENT, this.open)
    this.$bus.$off(TRANSFORM_PREVIEW_EVENT, this.openPreview)
  },
  methods: {
    open({ fields, rowIds, database, workspace, enabled }) {
      this.fields = fields
      this.selectedFieldIds = fields.map((field) => field.id)
      this.rowIds = rowIds
      this.database = database
      this.workspace = workspace
      this.enabled = enabled
      this.hideError()
      this.show()
    },
    toggleField(fieldId, checked) {
      this.selectedFieldIds = checked
        ? [...this.selectedFieldIds, fieldId]
        : this.selectedFieldIds.filter((id) => id !== fieldId)
    },
    openSettings() {
      this.hide()
      this.$refs.workspaceSettingsModal.show('generative-ai')
    },
    async transform(values) {
      this.hideError()
      this.loading = true
      try {
        const { data } = await JobService(this.$client).create(
          'transform_ai_cells',
          {
            ...values,
            // In the grid's column order.
            field_ids: this.fields
              .map((field) => field.id)
              .filter((id) => this.selectedFieldIds.includes(id)),
            row_ids: this.rowIds,
          }
        )
        // The job store polls it; its job type opens the preview when it's done.
        await this.$store.dispatch('job/create', data)
        this.hide()
        this.$store.dispatch('toast/info', {
          title: this.$t('aiTables.transformStartedTitle'),
          message: this.$t('aiTables.transformStarted'),
        })
      } catch (err) {
        this.handleError(err)
      } finally {
        this.loading = false
      }
    },
    cellKey,
    openPreview(job) {
      this.preview = job
      this.kept = job.proposals.map(cellKey)
      this.hideError()
      this.$refs.previewModal.show()
    },
    toggleKept(key, checked) {
      this.kept = checked
        ? [...this.kept, key]
        : this.kept.filter((kept) => kept !== key)
    },
    reject() {
      // Nothing was saved, so rejecting only closes the preview.
      this.$refs.previewModal.hide()
      this.$store.dispatch('toast/info', {
        title: this.$t('aiTables.rejectedTitle'),
        message: this.$t('aiTables.rejected'),
      })
    },
    async apply() {
      this.hideError()
      this.applying = true
      try {
        const cells = this.preview.proposals
          .filter((proposal) => this.kept.includes(cellKey(proposal)))
          .map(({ row_id: rowId, field_id: fieldId }) => ({
            row_id: rowId,
            field_id: fieldId,
          }))
        // ai_tables/views.py ApplyTransformView.
        const { data } = await this.$client.post(
          `/ai-tables/transform/${this.preview.id}/apply/`,
          { cells }
        )
        this.$refs.previewModal.hide()
        const skipped = data.skipped_row_ids.length
        this.$store.dispatch('toast/success', {
          title: this.$t('aiTables.appliedTitle'),
          message: skipped
            ? this.$t('aiTables.appliedSkipped', {
                count: data.written,
                skipped,
              })
            : this.$t('aiTables.applied', { count: data.written }),
        })
      } catch (err) {
        this.handleError(err)
      } finally {
        this.applying = false
      }
    },
  },
}
</script>
