<template>
  <Context ref="context" overflow-scroll max-height-if-outside-viewport>
    <ul class="select__items prevent-scroll">
      <li
        v-for="mode in modes"
        :key="mode.getType()"
        class="select__item select__item--no-options"
        :class="{ active: mode.type === view.mode }"
      >
        <a class="select__item-link" @click="select(mode)"
          ><span class="select__item-name">
            <i :class="`select__item-icon ${mode.getIconClass()}`"></i>
            <span class="select__item-name-text">{{ mode.getName() }}</span>
          </span>
          <div class="select__item-description">
            {{ mode.getDescription() }}
          </div>
        </a>
        <i
          v-if="mode.type === view.mode"
          class="select__item-active-icon iconoir-check"
        ></i>
      </li>
    </ul>
  </Context>
</template>

<script>
import context from '@baserow/modules/core/mixins/context'
import { notifyIf } from '@baserow/modules/core/utils/error'

export default {
  name: 'FormViewModeContext',
  mixins: [context],
  props: {
    view: {
      type: Object,
      required: true,
    },
  },
  computed: {
    modes() {
      return Object.values(this.$registry.getAll('formViewMode'))
    },
  },
  methods: {
    async select(mode) {
      this.hide()

      if (this.view.mode !== mode.type) {
        try {
          await this.$store.dispatch('view/update', {
            view: this.view,
            values: {
              mode: mode.type,
            },
          })
        } catch (error) {
          notifyIf(error, 'view')
        }
      }
    },
  },
}
</script>
