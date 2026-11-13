import { TextFieldType } from '@baserow/modules/database/fieldTypes'
import FieldPatternTextSubForm from './components/FieldPatternTextSubForm.vue'

/**
 * Single line text that must match the field's regular expression. The cells,
 * filters and sorting are the core text ones.
 *
 * Only the backend checks the pattern (field_patterns/patterns.py): it runs with a
 * timeout and unicode-aware \w, which the browser's RegExp can't promise, and a
 * value it refuses comes back as the save's error.
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
