import os


def setup(settings):
    """
    Called by baserow.config.settings.base for every installed plugin.
    """

    # How many rows of one generation run are sent to the model at the same time.
    settings.AI_TABLES_MAX_CONCURRENT_GENERATIONS = int(
        os.getenv("AI_TABLES_MAX_CONCURRENT_GENERATIONS", "") or 5
    )
    # How long changes to referenced fields are collected before an auto-update
    # regenerates the affected cells.
    settings.AI_TABLES_AUTO_UPDATE_DEBOUNCE_SECONDS = int(
        os.getenv("AI_TABLES_AUTO_UPDATE_DEBOUNCE_SECONDS", "") or 3
    )
