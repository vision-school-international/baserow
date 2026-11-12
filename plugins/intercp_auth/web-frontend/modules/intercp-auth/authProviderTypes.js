import { AuthProviderType } from '@baserow/modules/core/authProviderTypes'
import SignInAction from './components/SignInAction.vue'
import icon from './assets/sign-in.svg?url'

export class InterCPAuthProviderType extends AuthProviderType {
  static getType() {
    return 'intercp'
  }

  // Core requires an icon for every provider type.
  getIcon() {
    return icon
  }

  getName() {
    return 'InterCP'
  }

  getProviderName() {
    return this.getName()
  }

  // An action, not a button: core's login page hides login buttons when password
  // sign-in is disabled, but always renders login actions.
  getLoginActionComponent() {
    return SignInAction
  }

  canCreateNew() {
    return false
  }

  getOrder() {
    return 2
  }
}
