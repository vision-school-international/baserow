<template>
  <div>
    <div
      v-if="coverImage !== null"
      class="form-view__cover"
      :style="{
        'background-image': `url(${coverImage.url})`,
      }"
    ></div>
    <form
      v-if="!submitted"
      class="form-view__body"
      @submit.prevent="$emit('submit')"
    >
      <div class="form-view__heading">
        <Thumbnail v-if="logoImage !== null" :src="logoImage.url" width="200" />
        <h1 v-if="title !== ''" class="form-view__title">{{ title }}</h1>
        <div v-if="description !== ''" class="form-view__description">
          <FormViewDescription
            :value="description"
            read-only
          ></FormViewDescription>
        </div>
      </div>
      <!-- Not while editing one row: the page is then about that row. -->
      <FormRowsList v-if="list && !$route.query.edit_token" :list="list" />
      <FormPageField
        v-for="field in visibleFields"
        :ref="'field-' + field.field.id"
        :key="field.field.id"
        :value="values['field_' + field.field.id]"
        :slug="$route.params.slug"
        :field="field"
        :class="{ hidden: field._.hiddenViaQueryParam }"
        @input="updateValue('field_' + field.field.id, $event)"
      ></FormPageField>
      <div class="form-view__actions">
        <FormViewFooterLinks
          show-report-abuse
          :identifier="$route.params.slug"
        ></FormViewFooterLinks>
        <div class="form-view__submit">
          <Button
            type="primary"
            size="large"
            :loading="loading"
            :disabled="loading"
          >
            {{ submitText }}
          </Button>
        </div>
      </div>
    </form>
    <FormViewSubmitted
      v-else-if="submitted"
      :is-redirect="isRedirect"
      :submit-action-redirect-url="submitActionRedirectUrl"
      :submit-action-message="submitActionMessage"
    ></FormViewSubmitted>
  </div>
</template>

<script>
import FormViewModeForm from '@baserow/modules/database/components/view/form/FormViewModeForm'
import FormRowsList from './FormRowsList.vue'
import FormRowsService from '../services/formRows'

// Core's form plus the list; the template is core's with FormRowsList added.
export default {
  name: 'FormRowsForm',
  components: { FormRowsList },
  extends: FormViewModeForm,
  emits: ['submit'],
  data() {
    return { list: null }
  },
  async mounted() {
    try {
      const { data } = await FormRowsService(this.$client).getPublicList(
        this.$route.params.slug,
        this.$store.getters['page/view/public/getAuthToken']
      )
      this.list = data
    } catch {
      // The form still works without its list.
      this.list = null
    }
  },
}
</script>
