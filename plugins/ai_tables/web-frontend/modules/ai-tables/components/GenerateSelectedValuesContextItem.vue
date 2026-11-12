<template>
  <li class="context__menu-item">
    <a
      class="context__menu-item-link"
      :class="{ 'context__menu-item-link--loading': loading }"
      @click.prevent="generate"
    >
      <i class="context__menu-item-icon iconoir-magic-wand"></i>
      {{ $t('aiTables.generateSelected') }}
    </a>
  </li>
</template>

<script>
import JobService from '@baserow/modules/core/services/job'
import { notifyIf } from '@baserow/modules/core/utils/error'

export default {
  name: 'GenerateSelectedValuesContextItem',
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
  methods: {
    async generate() {
      if (this.loading) {
        return
      }
      this.loading = true
      try {
        const rows = await this.getRows()
        const { data } = await JobService(this.$client).create(
          'generate_ai_prompt_values',
          { field_id: this.field.id, row_ids: rows.map((row) => row.id) }
        )
        // The job store polls it; the cells update through the realtime events.
        await this.$store.dispatch('job/create', data)
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
