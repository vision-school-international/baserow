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

async function load() {
  try {
    const { data } = await FormRowsService($client).getSettings(props.view.id)
    settings.value = data
  } catch (error) {
    notifyIf(error, 'view')
  }
}

async function save(values) {
  try {
    const { data } = await FormRowsService($client).updateSettings(
      props.view.id,
      values
    )
    settings.value = data
  } catch (error) {
    notifyIf(error, 'view')
    await load()
  }
}

watch(() => props.view.id, load, { immediate: true })
</script>
