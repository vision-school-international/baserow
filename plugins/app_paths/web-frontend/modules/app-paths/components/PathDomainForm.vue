<template>
  <form @submit.prevent="submit">
    <FormGroup
      :label="$t('pathDomainForm.slugLabel')"
      :helper-text="
        $t('pathDomainForm.slugHelper', { url: `${host}/${slug || '…'}` })
      "
      small-label
      required
      :error-message="v$.slug.$errors[0]?.$message || serverErrorMessage"
    >
      <FormInput v-model="v$.slug.$model" @input="handleInput" />
    </FormGroup>
  </form>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { helpers, required } from '@vuelidate/validators'
import domainForm from '@baserow/modules/builder/mixins/domainForm'
import { getAppPathsHost } from '../domainTypes'

// One lowercase DNS label, like the backend's PathDomainType.SLUG.
const SLUG = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/

export default {
  name: 'PathDomainForm',
  mixins: [domainForm],
  emits: ['error'],
  setup() {
    return { v$: useVuelidate() }
  },
  data() {
    return {
      slug: '',
      values: {
        domain_name: '',
      },
    }
  },
  computed: {
    host() {
      return getAppPathsHost(this.$config)
    },
    serverErrorMessage() {
      // Same codes as SubDomainForm.
      const error = this.serverErrors.domain_name
      if (!error) {
        return ''
      }
      return error.code === 'unique'
        ? this.$t('pathDomainForm.taken')
        : this.$t('domainForm.invalidDomain')
    },
  },
  watch: {
    slug(value) {
      this.values.domain_name = `${value}.${this.host}`
    },
  },
  methods: {
    handleInput() {
      this.serverErrors.domain_name = null
      this.v$.slug.$touch()
      this.$emit('error', this.v$.$error)
    },
  },
  validations() {
    return {
      slug: {
        required: helpers.withMessage(this.$t('error.requiredField'), required),
        slug: helpers.withMessage(
          this.$t('pathDomainForm.invalidSlug'),
          (value) => !value || SLUG.test(value)
        ),
      },
    }
  },
}
</script>
