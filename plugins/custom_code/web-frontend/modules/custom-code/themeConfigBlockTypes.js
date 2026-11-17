import { ThemeConfigBlockType } from '@baserow/modules/builder/themeConfigBlockTypes'
import CustomCodeThemeConfigBlock from './components/CustomCodeThemeConfigBlock.vue'

/**
 * The application's own CSS and JavaScript, as the last tab of the theme
 * settings. It adds no CSS variables: the code is added to the page head by
 * the custom code plugin (plugin.js).
 */
export class CustomCodeThemeConfigBlockType extends ThemeConfigBlockType {
  static getType() {
    return 'custom_code'
  }

  get label() {
    return this.app.$i18n.t('customCodeThemeConfigBlock.label')
  }

  get component() {
    return CustomCodeThemeConfigBlock
  }

  getOrder() {
    return 100
  }
}
