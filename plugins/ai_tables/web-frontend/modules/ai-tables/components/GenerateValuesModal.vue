<template>
  <Modal ref="modal" :small="true">
    <h2 class="box__title">
      {{ $t('aiTables.generateTitle', { name: field.name }) }}
    </h2>
    <Error :error="error"></Error>
    <FormGroup v-if="view" small-label :label="$t('aiTables.generateRows')">
      <RadioGroup
        v-model="scope"
        :options="scopeOptions"
        :vertical-layout="true"
        type="radio"
      />
    </FormGroup>
    <FormGroup small-label class="margin-top-2">
      <Checkbox v-model="onlyEmpty" :disabled="jobIsRunning">
        {{ $t('aiTables.onlyEmpty') }}
      </Checkbox>
    </FormGroup>
    <ProgressBar
      v-if="job"
      class="margin-top-2"
      :value="job.progress_percentage"
      :status="jobHumanReadableState"
    />
    <div class="actions">
      <ul class="action__links">
        <li>
          <a v-if="jobIsRunning" @click.prevent="cancelJob()">
            {{ $t('action.cancel') }}
          </a>
          <a v-else @click.prevent="hide()">{{ $t('aiTables.close') }}</a>
        </li>
      </ul>
      <Button
        type="primary"
        :loading="loading || jobIsRunning"
        :disabled="loading || jobIsRunning"
        @click.prevent="generate"
      >
        {{ $t('aiTables.generate') }}
      </Button>
    </div>
  </Modal>
</template>

<script>
import error from '@baserow/modules/core/mixins/error'
import modal from '@baserow/modules/core/mixins/modal'
import job from '@baserow/modules/core/mixins/job'
import JobService from '@baserow/modules/core/services/job'

export default {
  name: 'GenerateValuesModal',
  mixins: [error, modal, job],
  props: {
    field: { type: Object, required: true },
    view: { type: Object, required: false, default: null },
  },
  data() {
    return {
      scope: 'view',
      onlyEmpty: true,
      loading: false,
    }
  },
  computed: {
    scopeOptions() {
      return [
        { value: 'view', label: this.$t('aiTables.rowsInView') },
        { value: 'table', label: this.$t('aiTables.rowsInTable') },
      ]
    },
  },
  methods: {
    async generate() {
      this.hideError()
      this.loading = true
      const params = { field_id: this.field.id, only_empty: this.onlyEmpty }
      if (this.view && this.scope === 'view') {
        params.view_id = this.view.id
      }
      try {
        const { data } = await JobService(this.$client).create(
          'generate_ai_prompt_values',
          params
        )
        await this.createAndMonitorJob(data)
      } catch (err) {
        this.handleError(err)
      } finally {
        this.loading = false
      }
    },
    // A failed job is reported by the job type's onJobFailed toast.
  },
}
</script>
