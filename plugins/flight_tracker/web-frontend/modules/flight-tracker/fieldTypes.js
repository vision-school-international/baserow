import { TextFieldType } from '@baserow/modules/database/fieldTypes'
import FieldFlightSubForm from './components/FieldFlightSubForm.vue'
import GridViewFieldFlight from './components/GridViewFieldFlight.vue'
import FunctionalGridViewFieldFlight from './components/FunctionalGridViewFieldFlight.vue'
import RowCardFieldFlight from './components/RowCardFieldFlight.vue'
import RowEditFieldFlight from './components/RowEditFieldFlight.vue'
import { FLIGHT_REGEX } from './status'

/**
 * A flight number, like AA6 or AAL6, stored as upper case text, so the filters
 * and sorting are the core text ones. Its live status comes from AirLabs
 * through the backend (flight_tracker/views.py) and is shown next to it.
 */
export class FlightFieldType extends TextFieldType {
  static getType() {
    return 'flight'
  }

  static getIconClass() {
    return 'iconoir-airplane'
  }

  getName() {
    return this.app.$i18n.t('flightTracker.fieldName')
  }

  getAlias() {
    return 'flight tracker airline status airport plane'
  }

  getFormComponent() {
    return FieldFlightSubForm
  }

  getGridViewFieldComponent() {
    return GridViewFieldFlight
  }

  getFunctionalGridViewFieldComponent() {
    return FunctionalGridViewFieldFlight
  }

  // Also the form's input (FieldType.getFormViewFieldComponents).
  getRowEditFieldComponent() {
    return RowEditFieldFlight
  }

  getCardComponent() {
    return RowCardFieldFlight
  }

  getCompatibleFilterFieldType() {
    return this.app.$registry.get('field', TextFieldType.getType())
  }

  // Shown before saving; the backend checks it again (flight.py clean_flight).
  getValidationError(field, value) {
    const error = super.getValidationError(field, value)
    if (error || !value) {
      return error
    }
    return FLIGHT_REGEX.test(value.replace(/\s+/g, '').toUpperCase())
      ? null
      : this.app.$i18n.t('flightTracker.invalid')
  }

  // No default value: the backend leaves text_default out (field_types.py).
  getDefaultValueFieldName() {
    return null
  }

  getDefaultValue(field) {
    return this.getEmptyValue(field)
  }
}
