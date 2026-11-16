<template>
  <div v-if="list.heading || list.fields.length" class="form-rows">
    <h2 v-if="list.heading" class="form-rows__heading">{{ list.heading }}</h2>
    <p v-if="list.intro" class="form-rows__intro">{{ list.intro }}</p>
    <template v-if="list.fields.length">
      <p v-if="!rows.length" class="form-rows__empty">
        {{ $t('formRows.noRows') }}
      </p>
      <template v-else>
        <div class="form-rows__tools">
          <input
            v-model="search"
            type="search"
            class="form-rows__search"
            :aria-label="$t('formRows.search')"
            :placeholder="$t('formRows.search')"
            @keydown.enter.prevent
          />
          <!-- Phone only: the cards have no column headers to click. -->
          <label class="form-rows__sort-select">
            {{ $t('formRows.sortBy') }}
            <select v-model="sortChoice">
              <option value="">{{ $t('formRows.viewOrder') }}</option>
              <template v-for="(field, index) in list.fields" :key="field.id">
                <option :value="`${index}:asc`">
                  {{
                    $t(`formRows.${sortKind(field)}Asc`, { name: field.name })
                  }}
                </option>
                <option :value="`${index}:desc`">
                  {{
                    $t(`formRows.${sortKind(field)}Desc`, { name: field.name })
                  }}
                </option>
              </template>
            </select>
          </label>
        </div>
        <p v-if="!shown.length" class="form-rows__empty">
          {{ $t('formRows.noMatches') }}
        </p>
        <div v-else class="form-rows__scroll">
          <table class="form-rows__table">
            <thead>
              <tr>
                <th
                  v-for="(field, index) in list.fields"
                  :key="field.id"
                  :aria-sort="ariaSort(index)"
                >
                  <button
                    type="button"
                    class="form-rows__sort"
                    @click="toggleSort(index)"
                  >
                    {{ field.name }}
                    <span v-if="sort.index === index" aria-hidden="true">{{
                      sort.desc ? '↓' : '↑'
                    }}</span>
                  </button>
                </th>
                <th v-if="hasEdit"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in shown" :key="row.id" class="form-rows__row">
                <td
                  v-for="(cell, index) in row.cells"
                  :key="list.fields[index].id"
                  class="form-rows__cell"
                >
                  <span class="form-rows__label">{{
                    list.fields[index].name
                  }}</span>
                  <span class="form-rows__value">
                    <template v-if="cell.chips">
                      <span
                        v-for="chip in cell.chips"
                        :key="chip.id"
                        class="form-rows__chip"
                        :class="'background-color--' + chip.color"
                        >{{ chip.value }}</span
                      >
                    </template>
                    <template v-else>{{ cell.text }}</template>
                  </span>
                </td>
                <td v-if="hasEdit" class="form-rows__edit">
                  <Button
                    v-if="row.edit_url"
                    tag="a"
                    type="secondary"
                    size="small"
                    :href="row.edit_url"
                    >{{ $t('formRows.edit') }}</Button
                  >
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <p v-if="list.more" class="form-rows__more">
        {{ $t('formRows.more', { count: list.more }) }}
      </p>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useNuxtApp } from '#app'
import { cellDisplay, sortKind, visibleRows } from '../utils'

const props = defineProps({
  // The backend's list payload (form_rows/handler.py list_payload).
  list: { type: Object, required: true },
})

const { $registry } = useNuxtApp()

// Search and sort only change what this visitor sees; nothing is saved.
const search = ref('')
const sort = ref({ index: null, desc: false })
// Other columns (the editor picked another view): back to the view's order.
watch(
  () => props.list.fields.map((field) => field.id).join(),
  () => {
    sort.value = { index: null, desc: false }
  }
)

const rows = computed(() =>
  props.list.rows.map((row) => ({
    ...row,
    cells: props.list.fields.map((field) =>
      cellDisplay($registry, field, row.values[`field_${field.id}`])
    ),
  }))
)
const shown = computed(() =>
  visibleRows(rows.value, props.list.fields, search.value, sort.value)
)
const hasEdit = computed(() => rows.value.some((row) => row.edit_url))

function toggleSort(index) {
  sort.value =
    sort.value.index === index
      ? { index, desc: !sort.value.desc }
      : { index, desc: false }
}

function ariaSort(index) {
  if (sort.value.index !== index) return 'none'
  return sort.value.desc ? 'descending' : 'ascending'
}

const sortChoice = computed({
  get: () =>
    sort.value.index === null
      ? ''
      : `${sort.value.index}:${sort.value.desc ? 'desc' : 'asc'}`,
  set: (choice) => {
    if (!choice) {
      sort.value = { index: null, desc: false }
      return
    }
    const [index, direction] = choice.split(':')
    sort.value = { index: Number(index), desc: direction === 'desc' }
  },
})
</script>
