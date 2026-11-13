<script>
import { AsYouType } from 'libphonenumber-js'
import FormViewFieldPatternText from './FormViewFieldPatternText.vue'

// The characters a phone number is typed with. Anything else, like "ext", is
// left as typed: the formatter would drop it.
const PHONE_CHARACTERS = /^[+\d\s().-]*$/

/**
 * The input of an international phone field, in forms and in the row modal. It
 * adds the spaces, brackets and dashes of the number's country while the user
 * types, and in forms checks the number with the backend like a pattern text
 * field does. The backend stores the number in the international format.
 */
export default {
  extends: FormViewFieldPatternText,
  computed: {
    inputType() {
      return 'tel'
    },
  },
  watch: {
    copy(value, previous) {
      // Only format what's typed at the end: formatting a deletion would put a
      // deleted bracket or dash straight back.
      const before = previous || ''
      if (
        typeof value !== 'string' ||
        value.length <= before.length ||
        !value.startsWith(before) ||
        !PHONE_CHARACTERS.test(value)
      ) {
        return
      }
      const formatted = new AsYouType(
        this.field.phone_default_country || undefined
      ).input(value)
      // A shorter result dropped something typed, like the space before "ext".
      if (formatted !== value && formatted.length >= value.length) {
        this.copy = formatted
      }
    },
  },
}
</script>
