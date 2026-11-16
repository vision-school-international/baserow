<template>
  <div v-if="list.heading || list.fields.length" class="form-rows">
    <h2 v-if="list.heading" class="form-rows__heading">{{ list.heading }}</h2>
    <p v-if="list.intro" class="form-rows__intro">{{ list.intro }}</p>
    <template v-if="list.fields.length">
      <p v-if="!rows.length" class="form-rows__empty">
        {{ $t('formRows.noRows') }}
      </p>
      <div v-else class="form-rows__scroll">
        <table class="form-rows__table">
          <thead>
            <tr>
              <th v-for="field in list.fields" :key="field.id">
                {{ field.name }}
              </th>
              <th v-if="hasEdit"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id" class="form-rows__row">
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
      <p v-if="list.more" class="form-rows__more">
        {{ $t('formRows.more', { count: list.more }) }}
      </p>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useNuxtApp } from '#app'
import { cellDisplay } from '../utils'

const props = defineProps({
  // The backend's list payload (form_rows/handler.py list_payload).
  list: { type: Object, required: true },
})

const { $registry } = useNuxtApp()

const rows = computed(() =>
  props.list.rows.map((row) => ({
    ...row,
    cells: props.list.fields.map((field) =>
      cellDisplay($registry, field, row.values[`field_${field.id}`])
    ),
  }))
)
const hasEdit = computed(() => rows.value.some((row) => row.edit_url))
</script>
