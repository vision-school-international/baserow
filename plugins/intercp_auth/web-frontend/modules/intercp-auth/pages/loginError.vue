<template>
  <div>
    <h1 class="auth__head-title">Sign in failed</h1>
    <p>{{ message }}</p>
    <Button tag="nuxt-link" :to="{ name: 'login' }" full-width size="large">
      Try again
    </Button>
  </div>
</template>

<script>
// shortcut: English-only copy, see SignInAction.vue.
// Keys match the error codes in the backend views.
const MESSAGES = {
  invalid_state: 'The sign-in link expired or was already used.',
  cancelled: 'Sign-in was cancelled.',
  provider_error: 'InterCP could not complete the sign-in. Please try again.',
  missing_email: 'Your InterCP account has no email address.',
  unverified_email: 'Your InterCP email address is not verified.',
  user_deactivated: 'Your account has been deactivated.',
  signup_disabled: 'New accounts are currently not allowed.',
  invitation_invalid: 'The invitation is invalid or has expired.',
  invitation_email_mismatch:
    'The invitation was sent to a different email address.',
}

export default {
  name: 'InterCPLoginError',
  computed: {
    message() {
      return MESSAGES[this.$route.query.error] || MESSAGES.provider_error
    },
  },
}
</script>
