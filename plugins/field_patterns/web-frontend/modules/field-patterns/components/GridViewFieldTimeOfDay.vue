<template>
  <div
    ref="cell"
    class="grid-view__cell active"
    :class="{ editing: editing, invalid: editing && !isValid() }"
    @contextmenu="stopContextIfEditing($event)"
  >
    <div v-if="!editing" class="grid-field-text">{{ display }}</div>
    <template v-else>
      <input
        ref="input"
        v-model="copy"
        type="text"
        class="grid-field-text__input"
      />
      <div v-show="!isValid()" class="grid-view__cell-error align-right">
        {{ getError() }}
      </div>
    </template>
  </div>
</template>

<script>
import GridViewFieldText from '@baserow/modules/database/components/view/grid/fields/GridViewFieldText'
import { formatTime, parseTime } from '../time'

/** Core's text cell, showing and editing the time in the field's clock. */
export default {
  name: 'GridViewFieldTimeOfDay',
  extends: GridViewFieldText,
  computed: {
    display() {
      return formatTime(this.value, this.field.time_format)
    },
  },
  methods: {
    prepareCopy(value) {
      return formatTime(value, this.field.time_format)
    },
    // As the backend stores it; a typo is left for the error to show.
    prepareValue(copy) {
      return parseTime(copy) ?? copy
    },
    // save() sends beforeSave(copy), not prepareValue (gridFieldInput.js):
    // without this an unchanged "2:30 PM" would be saved over "14:30".
    beforeSave(value) {
      return this.prepareValue(value)
    },
  },
}
</script>
