# Vision School image: the Baserow all-in-one image with our plugins baked in.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# The base image keeps plugins in /baserow/data/plugins, inside the data volume, where an
# existing volume would hide what the image ships. Keep them in the image instead.
ENV BASEROW_PLUGIN_DIR=/baserow/vsi-plugins
# Premium and enterprise are never loaded. The frontend is built with the same switch.
ENV BASEROW_OSS_ONLY=true
# Read by the backend and remapped for the frontend (web-frontend/env-remap.mjs).
ENV BRAND_NAME="Vision School"
# Backend reads it directly; the frontend through env-remap.mjs.
ENV FEATURE_FLAGS="agent-builder,agents,rbac_improvements,user_templates,semantic_search"

# No Baserow templates. The builder's theme files (ab_*_theme.json) stay: the builder
# loads themes from them (contrib/builder/tools/themes.py). A pattern that matches
# nothing stops the template sync from installing them as templates.
RUN find /baserow/backend/templates -name '*.json' ! -name 'ab_*_theme.json' -delete
ENV BASEROW_SYNC_TEMPLATES_PATTERN="^$"

# Backend only: the prod frontend cannot be rebuilt here, so plugin frontends are compiled
# into the web-frontend image (see web-frontend/Dockerfile, builder-prod).
COPY plugins/intercp_auth/baserow_plugin_info.json /baserow/vsi-plugins/intercp_auth/
COPY plugins/intercp_auth/backend /baserow/vsi-plugins/intercp_auth/backend
RUN /baserow/plugins/install_plugin.sh --folder /baserow/vsi-plugins/intercp_auth
COPY plugins/ai_tables/baserow_plugin_info.json /baserow/vsi-plugins/ai_tables/
COPY plugins/ai_tables/backend /baserow/vsi-plugins/ai_tables/backend
RUN /baserow/plugins/install_plugin.sh --folder /baserow/vsi-plugins/ai_tables
COPY plugins/sheets_sync/baserow_plugin_info.json /baserow/vsi-plugins/sheets_sync/
COPY plugins/sheets_sync/backend /baserow/vsi-plugins/sheets_sync/backend
RUN /baserow/plugins/install_plugin.sh --folder /baserow/vsi-plugins/sheets_sync
