from django.urls import path

from .views import ApplyTransformView

app_name = "ai_tables"

urlpatterns = [
    path(
        "transform/<int:job_id>/apply/",
        ApplyTransformView.as_view(),
        name="apply_transform",
    ),
]
