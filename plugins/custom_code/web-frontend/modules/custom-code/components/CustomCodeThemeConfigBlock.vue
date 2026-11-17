<template>
  <ThemeConfigBlockSection>
    <FormGroup
      small-label
      class="margin-bottom-2"
      :label="$t('customCodeThemeConfigBlock.css')"
      :helper-text="$t('customCodeThemeConfigBlock.cssHelper')"
    >
      <CodeEditor
        v-model="v$.values.custom_css.$model"
        language="css"
        :placeholder="$t('customCodeThemeConfigBlock.cssPlaceholder')"
        :modal-title="$t('customCodeThemeConfigBlock.css')"
      />
    </FormGroup>
    <FormGroup
      small-label
      class="margin-bottom-2"
      :label="$t('customCodeThemeConfigBlock.js')"
      :helper-text="$t('customCodeThemeConfigBlock.jsHelper')"
    >
      <CodeEditor
        v-model="v$.values.custom_js.$model"
        language="javascript"
        :placeholder="$t('customCodeThemeConfigBlock.jsPlaceholder')"
        :modal-title="$t('customCodeThemeConfigBlock.js')"
      />
    </FormGroup>
    <FormGroup
      small-label
      class="margin-bottom-2"
      :label="$t('customCodeThemeConfigBlock.assets')"
      :helper-text="$t('customCodeThemeConfigBlock.assetsHelper')"
    >
      <div
        v-for="row in rows"
        :key="row.key"
        v-sortable="{
          id: row.key,
          update: order,
          handle: '[data-sortable-handle]',
        }"
        class="custom-code-asset"
      >
        <a class="custom-code-asset__handle" data-sortable-handle>
          <i class="iconoir-drag"></i>
        </a>
        <div class="custom-code-asset__fields">
          <div class="custom-code-asset__options">
            <Dropdown v-model="row.type">
              <DropdownItem
                v-for="option in typeOptions"
                :key="option.value"
                :name="option.name"
                :value="option.value"
              />
            </Dropdown>
            <Dropdown v-if="row.type === 'script'" v-model="row.load">
              <DropdownItem
                v-for="option in loadOptions"
                :key="option.value"
                :name="option.name"
                :value="option.value"
              />
            </Dropdown>
            <Dropdown v-model="row.crossorigin">
              <DropdownItem
                v-for="option in crossoriginOptions"
                :key="option.value"
                :name="option.name"
                :value="option.value"
              />
            </Dropdown>
          </div>
          <FormInput
            v-model="row.url"
            :placeholder="$t('customCodeThemeConfigBlock.urlPlaceholder')"
            :error="row.url !== '' && !isValidUrl(row.url)"
          />
        </div>
        <ButtonIcon
          icon="iconoir-bin"
          :title="$t('customCodeThemeConfigBlock.remove')"
          @click="remove(row)"
        />
      </div>
      <ButtonText icon="iconoir-plus" @click="add">
        {{ $t('customCodeThemeConfigBlock.add') }}
      </ButtonText>
    </FormGroup>
  </ThemeConfigBlockSection>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { maxLength } from '@vuelidate/validators'
import themeConfigBlock from '@baserow/modules/builder/mixins/themeConfigBlock'
import form from '@baserow/modules/core/mixins/form'
import ThemeConfigBlockSection from '@baserow/modules/builder/components/theme/ThemeConfigBlockSection'
import CodeEditor from '@baserow/modules/core/components/CodeEditor.vue'
import { uuid } from '@baserow/modules/core/utils/string'

// custom_code/models.py MAX_CODE_LENGTH and MAX_ASSETS.
const MAX_CODE_LENGTH = 200000
const MAX_ASSETS = 50

/** The backend only accepts http(s) URLs (CustomAssetSerializer). */
const isValidUrl = (url) => {
  try {
    return ['http:', 'https:'].includes(new URL(url).protocol)
  } catch {
    return false
  }
}

const toRow = (asset) => ({
  key: uuid(),
  type: asset.type || 'stylesheet',
  url: asset.url || '',
  load: asset.load || '',
  crossorigin: asset.crossorigin || '',
})

export default {
  name: 'CustomCodeThemeConfigBlock',
  components: { ThemeConfigBlockSection, CodeEditor },
  mixins: [themeConfigBlock],
  setup() {
    return { v$: useVuelidate() }
  },
  data() {
    return {
      values: {
        custom_css: this.theme?.custom_css,
        custom_js: this.theme?.custom_js,
        custom_assets: this.theme?.custom_assets,
      },
      // The assets with a key for v-for and sorting, which isn't saved.
      rows: (
        this.theme?.custom_assets ||
        this.defaultValues?.custom_assets ||
        []
      ).map(toRow),
    }
  },
  computed: {
    typeOptions() {
      return [
        {
          value: 'stylesheet',
          name: this.$t('customCodeThemeConfigBlock.stylesheet'),
        },
        { value: 'script', name: this.$t('customCodeThemeConfigBlock.script') },
      ]
    },
    loadOptions() {
      return [
        { value: '', name: this.$t('customCodeThemeConfigBlock.loadNormal') },
        {
          value: 'defer',
          name: this.$t('customCodeThemeConfigBlock.loadDefer'),
        },
        {
          value: 'async',
          name: this.$t('customCodeThemeConfigBlock.loadAsync'),
        },
      ]
    },
    crossoriginOptions() {
      return [
        {
          value: '',
          name: this.$t('customCodeThemeConfigBlock.crossoriginNone'),
        },
        {
          value: 'anonymous',
          name: this.$t('customCodeThemeConfigBlock.crossoriginAnonymous'),
        },
        {
          value: 'use-credentials',
          name: this.$t('customCodeThemeConfigBlock.crossoriginCredentials'),
        },
      ]
    },
  },
  watch: {
    rows: {
      handler() {
        this.save()
      },
      deep: true,
    },
  },
  methods: {
    isValidUrl,
    /** After a failed save, the rows go back to the saved assets too. */
    async reset(deep = false) {
      await form.methods.reset.call(this, deep)
      this.rows = (this.values.custom_assets || []).map(toRow)
    },
    isAllowedKey(key) {
      return key.startsWith('custom_')
    },
    /** Saves the rows with a valid URL; a row being typed in waits for it. */
    save() {
      this.values.custom_assets = this.rows
        .filter((row) => isValidUrl(row.url))
        .map(({ type, url, load, crossorigin }) => ({
          type,
          url,
          // Only scripts are deferred or async.
          load: type === 'script' ? load : '',
          crossorigin,
        }))
    },
    add() {
      if (this.rows.length < MAX_ASSETS) {
        this.rows.push(toRow({}))
      }
    },
    remove(row) {
      this.rows = this.rows.filter((r) => r !== row)
    },
    order(newOrder) {
      const byKey = Object.fromEntries(this.rows.map((row) => [row.key, row]))
      this.rows = newOrder.map((key) => byKey[key])
    },
  },
  validations() {
    return {
      values: {
        custom_css: { maxLength: maxLength(MAX_CODE_LENGTH) },
        custom_js: { maxLength: maxLength(MAX_CODE_LENGTH) },
        custom_assets: {},
      },
    }
  },
}
</script>
