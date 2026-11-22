from django.urls import path

from .views import FlightStatusView

app_name = "flight_tracker"

urlpatterns = [
    path("<int:field_id>/status/", FlightStatusView.as_view(), name="status"),
]
