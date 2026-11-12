<template>
  <a
    ref="createViewLink"
    v-tooltip="tooltipText"
    class="select__footer-create-link"
    :class="{
      'select__footer-create-link--disabled':
        !viewType.isCompatibleWithDataSync(table.data_sync),
    }"
    :data-highlight="`create-view-${viewType.getType()}`"
    @click="select"
  >
    <i class="select__footer-create-icon" :class="viewType.iconClass"></i>
    {{ viewType.getName() }}
    <CreateViewModal
      ref="createModal"
      :table="table"
      :database="database"
      :view-type="viewType"
      @created="$emit('created', $event)"
    ></CreateViewModal>
    <i class="select__footer-create-link-icon iconoir-plus"></i>
  </a>
</template>

<script>
import CreateViewModal from '@baserow/modules/database/components/view/CreateViewModal'

export default {
  name: 'ViewsContext',
  components: {
    CreateViewModal,
  },
  props: {
    database: {
      type: Object,
      required: true,
    },
    table: {
      type: Object,
      required: true,
    },
    viewType: {
      type: Object,
      required: true,
    },
  },
  emits: ['created'],
  computed: {
    tooltipText() {
      if (!this.viewType.isCompatibleWithDataSync(this.table.data_sync)) {
        return this.$t('createViewLink.inCompatibleWithDataSync')
      }

      return null
    },
  },
  methods: {
    select() {
      if (!this.viewType.isCompatibleWithDataSync(this.table.data_sync)) {
        // Don't do anything in case the view type not compatible with a data sync
        // table.
      } else {
        this.$refs.createModal.show(this.$refs.createViewLink)
      }
    },
  },
}
</script>
