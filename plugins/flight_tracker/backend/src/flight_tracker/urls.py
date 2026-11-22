from django.urls import path

from .views import FlightStatusView, FlightTrackerRefreshView

app_name = "flight_tracker"

urlpatterns = [
    path("<int:field_id>/status/", FlightStatusView.as_view(), name="status"),
    path(
        "tracker/<int:field_id>/refresh/",
        FlightTrackerRefreshView.as_view(),
        name="tracker_refresh",
    ),
]
