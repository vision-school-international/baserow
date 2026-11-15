import { TextFieldType } from '@baserow/modules/database/fieldTypes'
import { DEFAULT_FORM_VIEW_FIELD_COMPONENT_KEY } from '@baserow/modules/database/constants'
import FieldPatternTextSubForm from './components/FieldPatternTextSubForm.vue'
import FormViewFieldPatternText from './components/FormViewFieldPatternText.vue'
import FieldInternationalPhoneSubForm from './components/FieldInternationalPhoneSubForm.vue'
import RowEditFieldInternationalPhone from './components/RowEditFieldInternationalPhone.vue'
import FieldTimeOfDaySubForm from './components/FieldTimeOfDaySubForm.vue'
import GridViewFieldTimeOfDay from './components/GridViewFieldTimeOfDay.vue'
import FunctionalGridViewFieldTimeOfDay from './components/FunctionalGridViewFieldTimeOfDay.vue'
import RowCardFieldTimeOfDay from './components/RowCardFieldTimeOfDay.vue'
import RowEditFieldTimeOfDay from './components/RowEditFieldTimeOfDay.vue'
import { parseTime } from './time'

/**
 * Single line text that must match the field's regular expression. The cells,
 * filters and sorting are the core text ones.
 *
 * Only the backend checks the pattern (field_patterns/patterns.py): it runs with a
 * timeout and unicode-aware \w, which the browser's RegExp can't promise, and a
 * value it refuses comes back as the save's error. Forms ask it while the
 * respondent types (FormViewFieldPatternText).
 */
export class PatternTextFieldType extends TextFieldType {
  static getType() {
    return 'pattern_text'
  }

  static getIconClass() {
    return 'iconoir-input-field'
  }

  getName() {
    return this.app.$i18n.t('fieldPatterns.fieldName')
  }

  getAlias() {
    return 'regex regular expression pattern validation format'
  }

  getFormComponent() {
    return FieldPatternTextSubForm
  }

  getFormViewFieldComponents(field, context) {
    const components = super.getFormViewFieldComponents(field, context)
    components[DEFAULT_FORM_VIEW_FIELD_COMPONENT_KEY].component =
      FormViewFieldPatternText
    return components
  }

  getCompatibleFilterFieldType() {
    return this.app.$registry.get('field', TextFieldType.getType())
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
 * A phone number of any country. The input formats the number while it's typed
 * (libphonenumber-js); the backend checks it with the full phone rules
 * (field_patterns/phones.py) and stores it in the international format, so the
 * cells, filters and sorting are the core text ones.
 */
export class InternationalPhoneFieldType extends TextFieldType {
  static getType() {
    return 'international_phone'
  }

  static getIconClass() {
    return 'iconoir-phone'
  }

  getName() {
    return this.app.$i18n.t('fieldPatterns.phoneFieldName')
  }

  getAlias() {
    return 'phone telephone mobile number international country'
  }

  getFormComponent() {
    return FieldInternationalPhoneSubForm
  }

  // Also the form's input (FieldType.getFormViewFieldComponents).
  getRowEditFieldComponent() {
    return RowEditFieldInternationalPhone
  }

  getCompatibleFilterFieldType() {
    return this.app.$registry.get('field', TextFieldType.getType())
  }

  // No default value, like PatternTextFieldType.
  getDefaultValueFieldName() {
    return null
  }

  getDefaultValue(field) {
    return this.getEmptyValue(field)
  }
}

/**
 * A Telegram username. The backend checks it (field_patterns/telegram.py) and
 * stores it as "@name", so the cells, filters and sorting are the core text ones.
 */
export class TelegramUsernameFieldType extends TextFieldType {
  static getType() {
    return 'telegram_username'
  }

  static getIconClass() {
    return 'iconoir-telegram'
  }

  getName() {
    return this.app.$i18n.t('fieldPatterns.telegramFieldName')
  }

  getAlias() {
    return 'telegram username handle messenger'
  }

  // No settings: the text type's form only holds a default value.
  getFormComponent() {
    return null
  }

  getCompatibleFilterFieldType() {
    return this.app.$registry.get('field', TextFieldType.getType())
  }

  // No default value, like PatternTextFieldType.
  getDefaultValueFieldName() {
    return null
  }

  getDefaultValue(field) {
    return this.getEmptyValue(field)
  }
}

/**
 * A time of day without a date. The backend (field_patterns/times.py) stores it
 * as 24 hour "HH:MM", so it sorts in time order and the filters are the core
 * text ones; the cells show it in the field's 24 or 12 hour clock (time.js).
 */
export class TimeOfDayFieldType extends TextFieldType {
  static getType() {
    return 'time_of_day'
  }

  static getIconClass() {
    return 'iconoir-clock'
  }

  getName() {
    return this.app.$i18n.t('fieldPatterns.timeFieldName')
  }

  getAlias() {
    return 'time hour clock am pm'
  }

  getFormComponent() {
    return FieldTimeOfDaySubForm
  }

  getGridViewFieldComponent() {
    return GridViewFieldTimeOfDay
  }

  getFunctionalGridViewFieldComponent() {
    return FunctionalGridViewFieldTimeOfDay
  }

  // Also the form's input (FieldType.getFormViewFieldComponents).
  getRowEditFieldComponent() {
    return RowEditFieldTimeOfDay
  }

  getCardComponent() {
    return RowCardFieldTimeOfDay
  }

  getCompatibleFilterFieldType() {
    return this.app.$registry.get('field', TextFieldType.getType())
  }

  // Shown in the cell before saving; the backend checks it again.
  getValidationError(field, value) {
    const error = super.getValidationError(field, value)
    // Empty cells are allowed; parseTime gives null for them too.
    if (error || value === null || value === undefined || value === '') {
      return error
    }
    return parseTime(value) === null
      ? this.app.$i18n.t('fieldPatterns.timeInvalid')
      : null
  }

  // No default value, like PatternTextFieldType.
  getDefaultValueFieldName() {
    return null
  }

  getDefaultValue(field) {
    return this.getEmptyValue(field)
  }
}
