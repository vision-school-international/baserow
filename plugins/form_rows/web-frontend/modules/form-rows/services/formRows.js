import addPublicAuthTokenHeader from '@baserow/modules/database/utils/publicView'

// Same shape as database/services/view/form.js.
export default (client) => ({
  getSettings(viewId) {
    return client.get(`/form-rows/views/${viewId}/`)
  },
  updateSettings(viewId, values) {
    return client.patch(`/form-rows/views/${viewId}/`, values)
  },
  getPublicList(slug, publicAuthToken = null) {
    const config = { headers: {} }
    if (publicAuthToken) {
      addPublicAuthTokenHeader(config, publicAuthToken)
    }
    return client.get(`/form-rows/public/${slug}/`, config)
  },
})
