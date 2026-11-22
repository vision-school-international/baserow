import { FieldType, TextFieldType } from '@baserow/modules/database/fieldTypes'
import FieldFlightTrackerSubForm from './components/FieldFlightTrackerSubForm.vue'
import GridViewFieldFlightTracker from './components/GridViewFieldFlightTracker.vue'
import FunctionalGridViewFieldFlightTracker from './components/FunctionalGridViewFieldFlightTracker.vue'
import RowCardFieldFlightTracker from './components/RowCardFieldFlightTracker.vue'
import RowEditFieldFlightTracker from './components/RowEditFieldFlightTracker.vue'
import { summary } from './tracker'
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

  // Replaced by the flight tracker; existing flight fields keep working.
  isVisibleInDropdown() {
    return false
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

/**
 * Read-only JSON with the live AirLabs data of the flight number in another
 * field of the row (flight_tracker/tracker.py to_cell), for people and for apps.
 */
export class FlightTrackerFieldType extends FieldType {
  static getType() {
    return 'flight_tracker'
  }

  static getIconClass() {
    return 'iconoir-airplane'
  }

  getName() {
    return this.app.$i18n.t('flightTracker.trackerName')
  }

  getAlias() {
    return 'flight tracker airline status airport plane airlabs'
  }

  getFormComponent() {
    return FieldFlightTrackerSubForm
  }

  getFormViewFieldComponents() {
    return {}
  }

  isReadOnlyField() {
    return true
  }

  getCanBePrimaryField() {
    return false
  }

  shouldFetchDataWhenAdded() {
    return true
  }

  getEmptyValue() {
    return null
  }

  getGridViewFieldComponent() {
    return GridViewFieldFlightTracker
  }

  getFunctionalGridViewFieldComponent() {
    return FunctionalGridViewFieldFlightTracker
  }

  getRowEditFieldComponent() {
    return RowEditFieldFlightTracker
  }

  getCardComponent() {
    return RowCardFieldFlightTracker
  }

  toHumanReadableString(field, value) {
    return summary(value, this.app.$i18n.t.bind(this.app.$i18n))
  }

  prepareValueForCopy(field, value) {
    return this.toHumanReadableString(field, value)
  }

  // The JSON itself, so copying between trackers keeps the data.
  prepareRichValueForCopy(field, value) {
    return value
  }

  // Like the backend's get_order: by scheduled departure (UTC), empty first.
  getSort(name, order) {
    return (a, b) => {
      const x = a[name]?.departure?.scheduled_utc || ''
      const y = b[name]?.departure?.scheduled_utc || ''
      if (x === y) {
        return 0
      }
      return (order === 'ASC' ? 1 : -1) * (x < y ? -1 : 1)
    }
  }

  getDocsDataType() {
    return 'object'
  }

  getDocsDescription() {
    return this.app.$i18n.t('flightTracker.docs')
  }

  getDocsRequestExample() {
    return null
  }

  getDocsResponseExample() {
    return {
      schema: 1,
      flight: 'AA6',
      error: null,
      status: 'landed',
      flight_iata: 'AA6',
      airline_name: 'American Airlines',
      departure: {
        airport_iata: 'HNL',
        terminal: null,
        gate: 'C3',
        scheduled: '2026-11-21 18:32',
        scheduled_utc: '2026-11-22 04:32',
        estimated: '2026-11-21 18:22',
        actual: '2026-11-21 18:25',
        delay_minutes: null,
      },
      arrival: {
        airport_iata: 'DFW',
        gate: 'D23',
        baggage: 'D9',
        scheduled: '2026-11-22 06:00',
        actual: '2026-11-22 05:41',
      },
    }
  }

  getContainsFilterFunction() {
    return (rowValue, humanReadableRowValue, filterValue) =>
      humanReadableRowValue.toLowerCase().includes(filterValue.toLowerCase())
  }

  canBeReferencedByFormulaField() {
    return false
  }
}
