import { defineNuxtPlugin, useHead } from '#imports'
import { BaserowPlugin } from '@baserow/modules/core/plugins'
import BrandLogo from './components/BrandLogo.vue'

class BrandPlugin extends BaserowPlugin {
  static getType() {
    return 'brand'
  }

  getLogoComponent() {
    return BrandLogo
  }

  // Above core's default of 50 (core/plugins.js).
  getLogoComponentOrder() {
    return 100
  }
}

export default defineNuxtPlugin({
  name: 'brand',
  // Runs after the plugins that register the guided tours and onboarding steps.
  dependsOn: ['core', 'database', 'builder', 'automation'],
  setup(nuxtApp) {
    const { brandName } = nuxtApp.$config.public
    const registry = nuxtApp.$registry

    registry.register('plugin', new BrandPlugin(nuxtApp))

    // Core sets 'Baserow' / '%s | Baserow' in core/head.js; a later entry wins.
    useHead({ title: brandName, titleTemplate: `%s | ${brandName}` })

    if (brandName !== 'Baserow') {
      // vue-i18n 11 legacy mode (i18n/i18n.config.ts) runs this on every
      // translated message (translate.ts:770, setter legacy.ts:1572). <i18n-t>
      // passes non-string output, which must go through untouched.
      // shortcut: also renames "Baserow" inside user values interpolated into a
      // message; switch to editing the locale strings if that ever matters.
      nuxtApp.$i18n.postTranslation = (message) =>
        typeof message === 'string'
          ? message.replaceAll('Baserow', brandName)
          : message
    }

    // Guided tours embed Baserow videos from YouTube, and the onboarding "more"
    // step sends the answers to baserow.io.
    for (const type of ['sidebar', 'database', 'builder', 'automation']) {
      registry.unregister('guidedTour', type)
    }
    registry.unregister('onboarding', 'more')
  },
})
