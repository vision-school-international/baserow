import { DataSyncType } from '@baserow/modules/database/dataSyncTypes'
import { TwoWaySyncStrategyType } from '@baserow/modules/database/twoWaySyncStrategyTypes'
import GoogleSheetsDataSync from './components/GoogleSheetsDataSync'

// Matches the backend `google_sheets_push` strategy.
export class GoogleSheetsPushStrategyType extends TwoWaySyncStrategyType {
  static getType() {
    return 'google_sheets_push'
  }

  getDescription() {
    return this.app.$i18n.t('googleSheetsDataSync.twoWayDescription')
  }
}

// Same shape as core's ICalCalendarDataSyncType (database/dataSyncTypes.js).
export class GoogleSheetsDataSyncType extends DataSyncType {
  static getType() {
    return 'google_sheets'
  }

  getIconClass() {
    return 'iconoir-google-drive-sync'
  }

  getName() {
    return this.app.$i18n.t('googleSheetsDataSync.name')
  }

  getFormComponent() {
    return GoogleSheetsDataSync
  }

  getTwoWayDataSyncStrategy() {
    return GoogleSheetsPushStrategyType.getType()
  }
}
