from django.urls import re_path

from .views import FormRowsSettingsView, PublicFormRowsView

app_name = "form_rows"

urlpatterns = [
    re_path(
        r"^views/(?P<view_id>[0-9]+)/$",
        FormRowsSettingsView.as_view(),
        name="settings",
    ),
    # Slugs are URL-safe base64 (View.create_new_slug).
    re_path(r"^public/(?P<slug>[\w-]+)/$", PublicFormRowsView.as_view(), name="public"),
]
