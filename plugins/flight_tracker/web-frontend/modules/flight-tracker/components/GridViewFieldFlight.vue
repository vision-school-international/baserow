<script>
import GridViewFieldText from '@baserow/modules/database/components/view/grid/fields/GridViewFieldText'

/** Core's text cell, saving the flight number as the backend stores it. */
export default {
  name: 'GridViewFieldFlight',
  extends: GridViewFieldText,
  methods: {
    // save() sends beforeSave(copy) (gridFieldInput.js).
    beforeSave(value) {
      return (value || '').replace(/\s+/g, '').toUpperCase()
    },
  },
}
</script>
