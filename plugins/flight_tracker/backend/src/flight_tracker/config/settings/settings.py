import os


def setup(settings):
    """
    Called by baserow.config.settings.base for every installed plugin.
    """

    # How often flights of fields set to refresh on a schedule are looked up again.
    settings.FLIGHT_TRACKER_INTERVAL_MINUTES = int(
        os.getenv("FLIGHT_TRACKER_INTERVAL_MINUTES", "") or 10
    )
    # How long a status shown in a view is reused before it's looked up again.
    settings.FLIGHT_TRACKER_VIEW_TTL_MINUTES = int(
        os.getenv("FLIGHT_TRACKER_VIEW_TTL_MINUTES", "") or 5
    )
    # AirLabs lookups the whole server may make per day (views and schedule).
    # 30 keeps the free plan's 1000 a month; raise it with the plan.
    settings.FLIGHT_TRACKER_MAX_LOOKUPS_PER_DAY = int(
        os.getenv("FLIGHT_TRACKER_MAX_LOOKUPS_PER_DAY", "") or 30
    )
