<template>
  <FormGroup
    v-if="searchableFields.length > 0"
    class="margin-bottom-1"
    small-label
    :label="$t('formViewField.linkRowSearchFields')"
    :helper-text="$t('formViewField.linkRowSearchFieldsHelper')"
  >
    <Dropdown
      :value="selectedIds"
      :multiple="true"
      :fixed-items="true"
      :disabled="readOnly"
      :placeholder="$t('formViewField.linkRowSearchFieldsPlaceholder')"
      @input="
        $emit('updated-field-options', { link_row_search_field_ids: $event })
      "
    >
      <DropdownItem
        v-for="searchable in searchableFields"
        :key="searchable.id"
        :name="searchable.name"
        :value="searchable.id"
        :icon="searchable.icon"
      ></DropdownItem>
    </Dropdown>
  </FormGroup>
</template>

<script>
import FieldService from '@baserow/modules/database/services/field'
import { notifyIf } from '@baserow/modules/core/utils/error'

/**
 * Chooses the linked table's fields, besides its primary field, that the
 * form's row search also matches (`link_row_search_field_ids`).
 */
export default {
  name: 'FormViewFieldOptionsLinkRowSearchFields',
  props: {
    readOnly: {
      type: Boolean,
      required: true,
    },
    field: {
      type: Object,
      required: true,
    },
    fieldOptions: {
      type: Object,
      required: true,
    },
  },
  emits: ['updated-field-options'],
  data() {
    return { searchableFields: [] }
  },
  computed: {
    selectedIds() {
      // Ids of fields deleted since are left out, like the backend does.
      const ids = this.fieldOptions.link_row_search_field_ids || []
      return ids.filter((id) => this.searchableFields.some((f) => f.id === id))
    },
  },
  watch: {
    'field.link_row_table_id'() {
      this.fetchFields()
    },
  },
  mounted() {
    this.fetchFields()
  },
  methods: {
    async fetchFields() {
      this.searchableFields = []
      if (!this.field.link_row_table_id) {
        return
      }
      try {
        const { data } = await FieldService(this.$client).fetchAll(
          this.field.link_row_table_id
        )
        this.searchableFields = data
          .filter((f) => !f.primary)
          .filter((f) => this.$registry.get('field', f.type).isSearchable(f))
          .map((f) => ({
            ...f,
            icon: this.$registry.get('field', f.type).getIconClass(),
          }))
      } catch (error) {
        notifyIf(error, 'field')
      }
    },
  },
}
</script>
