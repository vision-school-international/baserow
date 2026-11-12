# Vision School image: the Baserow all-in-one image with our plugins baked in.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# The base image keeps plugins in /baserow/data/plugins, inside the data volume, where an
# existing volume would hide what the image ships. Keep them in the image instead.
ENV BASEROW_PLUGIN_DIR=/baserow/vsi-plugins
# Premium and enterprise are never loaded. The frontend is built with the same switch.
ENV BASEROW_OSS_ONLY=true

# Backend only: the prod frontend cannot be rebuilt here, so plugin frontends are compiled
# into the web-frontend image (see web-frontend/Dockerfile, builder-prod).
COPY plugins/intercp_auth/baserow_plugin_info.json /baserow/vsi-plugins/intercp_auth/
COPY plugins/intercp_auth/backend /baserow/vsi-plugins/intercp_auth/backend
RUN /baserow/plugins/install_plugin.sh --folder /baserow/vsi-plugins/intercp_auth
