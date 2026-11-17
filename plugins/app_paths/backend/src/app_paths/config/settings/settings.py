import os


def setup(settings):
    """
    Called by baserow.config.settings.base for every installed plugin.

    BASEROW_APP_PATHS_HOST is the shared address the sites are published under,
    e.g. "apps.example.com". Empty turns path publishing off. The web-frontend
    reads the same variable (env-remap.mjs). Changing it later leaves sites
    published under the old host unreachable until they are re-added.
    """

    settings.BASEROW_APP_PATHS_HOST = (
        os.getenv("BASEROW_APP_PATHS_HOST", "").strip().lower()
    )
