import { Registerable } from '@baserow/modules/core/registry'
import { JobType } from '@baserow/modules/core/jobTypes'
import { BaserowPlugin } from '@baserow/modules/core/plugins'
import { AIProviderModelFeatureType } from '@baserow/modules/core/aiProviderModelFeatureTypes'
import GenerateValuesContextItem from './components/GenerateValuesContextItem.vue'
import TransformCellsModal, {
  TRANSFORM_PREVIEW_EVENT,
} from './components/TransformCellsModal.vue'
import TransformCellsContextItem from './components/TransformCellsContextItem.vue'

// The transform modal lives in the app layout: the grid's cell-selection menu
// unmounts its items on the first click outside the grid.
export class AITablesPlugin extends BaserowPlugin {
  static getType() {
    return 'ai_tables'
  }

  getAppLayoutComponent() {
    return TransformCellsModal
  }
}

export class TransformAICellsJobType extends JobType {
  static getType() {
    return 'transform_ai_cells'
  }

  getName() {
    return this.$t('aiTables.transformCells')
  }

  // Nothing is saved yet: the preview lets the user keep or reject each change.
  async onJobDone(job) {
    if (job.proposals?.length) {
      this.app.$bus.$emit(TRANSFORM_PREVIEW_EVENT, job)
      return
    }
    await this.app.$store.dispatch('toast/info', {
      title: this.$t('aiTables.noChangesTitle'),
      message: job.failed_row_ids?.length
        ? this.$t('aiTables.previewFailed', {
            count: job.failed_row_ids.length,
          })
        : this.$t('aiTables.noChanges'),
    })
  }

  async onJobFailed(job) {
    await this.app.$store.dispatch('toast/error', {
      title: this.$t('aiTables.transformFailed'),
      message: job.human_readable_error,
    })
  }
}

// Same pattern as DuplicateTableJobType (database/jobTypes.js).
export class GenerateAIPromptValuesJobType extends JobType {
  static getType() {
    return 'generate_ai_prompt_values'
  }

  getName() {
    return this.$t('aiTables.generateValues')
  }

  // Row-level failures arrive as realtime events; this is the whole job failing.
  async onJobFailed(job) {
    await this.app.$store.dispatch('toast/error', {
      title: this.$t('aiTables.generateFailed'),
      message: job.human_readable_error,
    })
  }
}

// Same type as the backend's (ai_provider_feature_types.py), like
// AIAgentAIProviderModelFeatureType (integrations/ai/aiProviderModelFeatureTypes.js).
export class AIPromptFieldsFeatureType extends AIProviderModelFeatureType {
  static getType() {
    return 'ai_fields'
  }

  getName() {
    return this.$t('aiTables.featureName')
  }

  getDescription() {
    return this.$t('aiTables.featureDescription')
  }
}

// Rendered by FieldContext.vue from the 'fieldContextItem' registry.
export class GenerateValuesContextItemType extends Registerable {
  static getType() {
    return 'generate_ai_prompt_values'
  }

  getComponent() {
    return GenerateValuesContextItem
  }
}

export class TransformCellsSelectionItemType extends Registerable {
  static getType() {
    return 'transform_ai_cells'
  }

  getComponent() {
    return TransformCellsContextItem
  }
}
