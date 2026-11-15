<script>
import RowEditFieldText from '@baserow/modules/database/components/row/RowEditFieldText'
import { formatTime, parseTime } from '../time'

/**
 * Core's text input of the row modal and forms, editing the time in the field's
 * clock. The backend checks and stores it as 24 hour "HH:MM".
 */
export default {
  name: 'RowEditFieldTimeOfDay',
  extends: RowEditFieldText,
  methods: {
    prepareCopy(value) {
      return formatTime(value, this.field.time_format)
    },
    prepareValue(copy) {
      return parseTime(copy) ?? copy
    },
    // save() sends beforeSave(copy), not prepareValue (rowEditFieldInput.js).
    beforeSave(value) {
      return this.prepareValue(value)
    },
  },
}
</script>
