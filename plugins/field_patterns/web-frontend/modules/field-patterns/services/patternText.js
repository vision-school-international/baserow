import addPublicAuthTokenHeader from '@baserow/modules/database/utils/publicView'

export default (client) => {
  return {
    /**
     * Checks a form value against its pattern text or phone field, without saving
     * it (field_patterns/views.py CheckFormValueView).
     */
    checkFormValue(slug, fieldId, value, publicAuthToken = null) {
      const config = { headers: {} }
      if (publicAuthToken) {
        addPublicAuthTokenHeader(config, publicAuthToken)
      }
      return client.post(
        `/database/fields/field-patterns/form/${slug}/field/${fieldId}/check/`,
        { value },
        config
      )
    },
  }
}
