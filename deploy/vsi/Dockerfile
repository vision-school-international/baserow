# Vision School image: the Baserow all-in-one image with our plugins baked in.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# The base image keeps plugins in /baserow/data/plugins, inside the data volume, where an
# existing volume would hide what the image ships. Keep them in the image instead.
ENV BASEROW_PLUGIN_DIR=/baserow/vsi-plugins

COPY plugins/intercp_auth /baserow/vsi-plugins/intercp_auth
RUN /baserow/plugins/install_plugin.sh --folder /baserow/vsi-plugins/intercp_auth
