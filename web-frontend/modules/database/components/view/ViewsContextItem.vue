<template>
  <li
    class="select__item"
    :class="{
      active: view._.selected,
      'select__item--loading': view._.loading,
      'select__item--no-options': readOnly,
    }"
  >
    <a class="select__item-link" @click="select(view)">
      <div class="select__item-name">
        <i
          class="select__item-icon"
          :class="`${view._.type.colorClass} ${view._.type.iconClass}`"
        ></i>
        <span class="select__item-name-text"
          ><EditableViewName ref="rename" :view="view"></EditableViewName
        ></span>
      </div>
    </a>
    <i
      v-if="view._.selected"
      class="select__item-active-icon iconoir-check"
    ></i>
    <template v-if="!readOnly && showViewContext">
      <a
        ref="contextLink"
        class="select__item-options"
        @click="$refs.context.toggle($refs.contextLink, 'bottom', 'right', 0)"
        @mousedown.stop
      >
        <i class="baserow-icon-more-vertical"></i>
      </a>
      <ViewContext
        ref="context"
        :database="database"
        :table="table"
        :view="view"
        :store-prefix="storePrefix"
        @enable-rename="enableRename"
      ></ViewContext>
    </template>
  </li>
</template>

<script>
import context from '@baserow/modules/core/mixins/context'
import ViewContext from '@baserow/modules/database/components/view/ViewContext'
import EditableViewName from '@baserow/modules/database/components/view/EditableViewName'

export default {
  name: 'ViewsContextItem',
  components: { EditableViewName, ViewContext },
  mixins: [context],
  props: {
    database: {
      type: Object,
      required: true,
    },
    view: {
      type: Object,
      required: true,
    },
    table: {
      type: Object,
      required: true,
    },
    readOnly: {
      type: Boolean,
      required: false,
      default: true,
    },
    storePrefix: {
      type: String,
      required: true,
    },
  },
  emits: ['selected'],
  computed: {
    showViewContext() {
      return (
        this.$hasPermission(
          'database.table.run_export',
          this.table,
          this.database.workspace.id
        ) ||
        this.$hasPermission(
          'database.table.import_rows',
          this.table,
          this.database.workspace.id
        ) ||
        this.$hasPermission(
          'database.table.view.duplicate',
          this.table,
          this.database.workspace.id
        ) ||
        this.$hasPermission(
          'database.table.create_webhook',
          this.table,
          this.database.workspace.id
        ) ||
        this.$hasPermission(
          'database.table.view.update',
          this.view,
          this.database.workspace.id
        ) ||
        this.$hasPermission(
          'database.table.view.delete',
          this.view,
          this.database.workspace.id
        )
      )
    },
  },
  methods: {
    enableRename() {
      this.$refs.rename.edit()
    },
    select(view) {
      this.$emit('selected', view)
    },
  },
}
</script>
