import { ViewFilterType } from '@baserow/modules/database/viewFilters'
import ViewFilterTypeFlightStatus from './components/ViewFilterTypeFlightStatus.vue'

/**
 * Rows whose flight tracker has a status, an error, or no data yet
 * (flight_tracker/view_filters.py).
 */
export class FlightStatusViewFilterType extends ViewFilterType {
  static getType() {
    return 'flight_status'
  }

  getName() {
    return this.app.$i18n.t('flightTracker.filterName')
  }

  getExample() {
    return 'scheduled | en-route | landed | not_found | invalid_flight_number | none'
  }

  getInputComponent() {
    return ViewFilterTypeFlightStatus
  }

  getCompatibleFieldTypes() {
    return ['flight_tracker']
  }

  matches(rowValue, filterValue) {
    if (['scheduled', 'en-route', 'landed'].includes(filterValue)) {
      return rowValue?.status === filterValue
    }
    if (['not_found', 'invalid_flight_number'].includes(filterValue)) {
      return rowValue?.error === filterValue
    }
    if (filterValue === 'none') {
      return !rowValue || (!rowValue.status && !rowValue.error)
    }
    return true
  }
}
