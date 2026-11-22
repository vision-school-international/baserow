import { askStatus, describe, getStatus } from './status'

// Refreshes the shown status while the cell stays on screen.
const REFRESH_MS = 5 * 60 * 1000

/** For the components that get the row: the grid cell, card and row modal. */
export default {
  computed: {
    flightStatus() {
      return this.row?.id
        ? getStatus(this.field.id, this.row.id, this.value)
        : null
    },
    flightText() {
      return describe(this.flightStatus, this.$t)
    },
  },
  watch: {
    value() {
      this.askFlightStatus(true)
    },
  },
  mounted() {
    this.askFlightStatus()
    this.flightTimer = setInterval(() => this.askFlightStatus(), REFRESH_MS)
  },
  beforeUnmount() {
    clearInterval(this.flightTimer)
  },
  methods: {
    askFlightStatus(force = false) {
      // Forms and new rows have no row to look up yet, and public views no
      // signed-in user (the status endpoint needs one).
      if (
        this.row?.id &&
        this.value &&
        this.$store?.getters['auth/isAuthenticated']
      ) {
        askStatus(this.$client, this.field.id, this.row.id, this.value, force)
      }
    },
  },
}
