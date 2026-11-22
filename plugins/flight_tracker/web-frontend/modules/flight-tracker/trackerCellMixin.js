import { askFill, summary } from './tracker'

// While a cell stays on screen it asks again; the backend only looks flights up
// when the field's interval has passed.
const REFRESH_MS = 5 * 60 * 1000

/** For the components that get the row: the grid cell, card and row modal. */
export default {
  computed: {
    trackerText() {
      return summary(this.value, this.$t)
    },
  },
  mounted() {
    this.askTrackerFill()
    this.trackerTimer = setInterval(() => this.askTrackerFill(), REFRESH_MS)
  },
  beforeUnmount() {
    clearInterval(this.trackerTimer)
  },
  methods: {
    askTrackerFill() {
      // Public views have no signed-in user (the endpoint needs one).
      if (
        this.row?.id &&
        this.field.flight_code_field_id &&
        this.$store?.getters['auth/isAuthenticated']
      ) {
        askFill(this.$client, this.field.id, this.row.id)
      }
    },
  },
}
