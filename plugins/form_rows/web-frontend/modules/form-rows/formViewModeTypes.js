import { FormViewFormModeType } from '@baserow/modules/database/formViewModeTypes'
import FormRowsForm from './components/FormRowsForm.vue'
import FormRowsPreview from './components/FormRowsPreview.vue'

/**
 * A normal form plus a list of a view's rows above the fields (backend:
 * form_rows/form_view_mode_types.py).
 */
export class FormWithRowsModeType extends FormViewFormModeType {
  static getType() {
    return 'form_with_rows'
  }

  getName() {
    return this.app.$i18n.t('formRows.modeName')
  }

  getDescription() {
    return this.app.$i18n.t('formRows.modeDescription')
  }

  getIconClass() {
    return 'iconoir-list'
  }

  getPreviewComponent() {
    return FormRowsPreview
  }

  getFormComponent() {
    return FormRowsForm
  }
}
