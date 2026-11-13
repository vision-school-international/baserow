from django.urls import path

from .views import CheckFormValueView

app_name = "field_patterns"

urlpatterns = [
    path(
        "form/<str:slug>/field/<int:field_id>/check/",
        CheckFormValueView.as_view(),
        name="check_form_value",
    ),
]
