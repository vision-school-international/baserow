<template>
  <div>
    <div v-if="!readOnly && settings" class="form-rows-settings">
      <FormGroup
        :label="$t('formRows.listView')"
        small-label
        class="margin-bottom-2"
      >
        <Dropdown
          :value="settings.list_view_id"
          :fixed-items="true"
          small
          @input="save({ list_view_id: $event })"
        >
          <DropdownItem
            v-for="option in listViews"
            :key="option.id"
            :name="option.name"
            :value="option.id"
          ></DropdownItem>
        </Dropdown>
      </FormGroup>
      <FormGroup
        :label="$t('formRows.heading')"
        small-label
        class="margin-bottom-2"
      >
        <FormInput
          v-model="settings.heading"
          :placeholder="$t('formRows.headingPlaceholder')"
          @blur="save({ heading: settings.heading })"
        />
      </FormGroup>
      <FormGroup
        :label="$t('formRows.intro')"
        small-label
        class="margin-bottom-2"
      >
        <FormInput
          v-model="settings.intro"
          @blur="save({ intro: settings.intro })"
        />
      </FormGroup>
      <Checkbox
        :checked="settings.allow_edit"
        @input="save({ allow_edit: $event })"
        >{{ $t('formRows.allowEdit') }}</Checkbox
      >
      <p v-if="settings.allow_edit" class="form-rows-settings__warning">
        {{ $t('formRows.allowEditWarning') }}
      </p>
    </div>
    <div v-if="settings" class="form-rows-settings__preview">
      <FormRowsList :list="settings.list" />
    </div>
    <FormViewModePreviewForm
      v-bind="$attrs"
      :view="view"
      :read-only="readOnly"
    ></FormViewModePreviewForm>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useNuxtApp } from '#app'
import FormViewModePreviewForm from '@baserow/modules/database/components/view/form/FormViewModePreviewForm'
import { notifyIf } from '@baserow/modules/core/utils/error'
import FormRowsList from './FormRowsList.vue'
import FormRowsService from '../services/formRows'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  view: { type: Object, required: true },
  readOnly: { type: Boolean, required: true },
})

const { $client, $store } = useNuxtApp()
const settings = ref(null)

// Views of the form's own table that list rows (backend checks can_list_rows).
const listViews = computed(() =>
  $store.getters['view/getAll'].filter(
    (view) => view.table_id === props.view.table_id && view.type !== 'form'
  )
)

// A response never overwrites the text boxes: the editor may be typing in one
// while another setting's save comes back. Each box saves its own text on blur.
function apply(data) {
  const typed = settings.value
    ? { heading: settings.value.heading, intro: settings.value.intro }
    : {}
  settings.value = { ...data, ...typed }
}

// Responses for a form the editor has since left are dropped.
async function load() {
  const viewId = props.view.id
  try {
    const { data } = await FormRowsService($client).getSettings(viewId)
    if (viewId === props.view.id) apply(data)
  } catch (error) {
    if (viewId === props.view.id) notifyIf(error, 'view')
  }
}

async function save(values) {
  const viewId = props.view.id
  try {
    const { data } = await FormRowsService($client).updateSettings(
      viewId,
      values
    )
    if (viewId === props.view.id) apply(data)
  } catch (error) {
    notifyIf(error, 'view')
    if (viewId === props.view.id) await load()
  }
}

watch(
  () => props.view.id,
  () => {
    // Another form: its own text, not the last form's.
    settings.value = null
    load()
  },
  { immediate: true }
)
</script>
