<template>
  <div v-if="showReportLink" class="form-view__footer-links">
    <a
      class="form-view__report-abuse"
      href="#"
      @click.prevent="$refs.reportAbuseModal.show()"
    >
      {{ $t('formViewFooterLinks.reportAbuse') }}
    </a>
    <ReportAbuseModal
      ref="reportAbuseModal"
      resource-type="database_view"
      :identifier="identifier"
      :request-config="requestConfig"
    ></ReportAbuseModal>
  </div>
</template>

<script>
import ReportAbuseModal from '@baserow/modules/core/components/abuseReport/ReportAbuseModal'
import addPublicAuthTokenHeader from '@baserow/modules/database/utils/publicView'

export default {
  name: 'FormViewFooterLinks',
  components: { ReportAbuseModal },
  props: {
    showReportAbuse: {
      type: Boolean,
      required: false,
      default: false,
    },
    identifier: {
      type: String,
      required: false,
      default: '',
    },
  },
  computed: {
    showReportLink() {
      return (
        this.showReportAbuse &&
        this.$store.getters['settings/get'].allow_reporting_abuse !== false
      )
    },
    requestConfig() {
      const publicAuthToken =
        this.$store.getters['page/view/public/getAuthToken']
      return publicAuthToken
        ? addPublicAuthTokenHeader({}, publicAuthToken)
        : {}
    },
  },
}
</script>
