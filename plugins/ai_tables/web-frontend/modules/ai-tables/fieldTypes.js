import {
  LongTextFieldType,
  SingleSelectFieldType,
} from '@baserow/modules/database/fieldTypes'
import AIPromptTextFieldSubForm from './components/AIPromptTextFieldSubForm.vue'
import AIPromptChoiceFieldSubForm from './components/AIPromptChoiceFieldSubForm.vue'
import GenerateSelectedValuesContextItem from './components/GenerateSelectedValuesContextItem.vue'

/**
 * The cells, sorting and editing are the core long text and single select ones;
 * these types only add the prompt settings and the generate actions.
 */
const AIPromptFieldTypeMixin = (Base, baseType) =>
  class extends Base {
    static getIconClass() {
      return 'iconoir-magic-wand'
    }

    getAlias() {
      return 'ai prompt generate llm gpt'
    }

    // Filters and the backend use the core type's (field_types.py).
    getCompatibleFilterFieldType() {
      return this.app.$registry.get('field', baseType)
    }

    getGridViewContextItemsOnCellsSelection() {
      return [GenerateSelectedValuesContextItem]
    }

    // The model writes the cell, so it isn't asked for in forms.
    getFormViewFieldComponents() {
      return {}
    }

    getCanBePrimaryField() {
      return false
    }
  }

export class AIPromptTextFieldType extends AIPromptFieldTypeMixin(
  LongTextFieldType,
  LongTextFieldType.getType()
) {
  static getType() {
    return 'ai_prompt_text'
  }

  getName() {
    return this.app.$i18n.t('aiTables.textFieldName')
  }

  getFormComponent() {
    return AIPromptTextFieldSubForm
  }
}

export class AIPromptChoiceFieldType extends AIPromptFieldTypeMixin(
  SingleSelectFieldType,
  SingleSelectFieldType.getType()
) {
  static getType() {
    return 'ai_prompt_choice'
  }

  getName() {
    return this.app.$i18n.t('aiTables.choiceFieldName')
  }

  getFormComponent() {
    return AIPromptChoiceFieldSubForm
  }
}
