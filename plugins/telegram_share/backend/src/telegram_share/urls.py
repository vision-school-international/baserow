from django.urls import re_path

from .views import share_card

app_name = "telegram_share"

urlpatterns = [
    # Slugs are URL-safe base64 (View.create_new_slug).
    re_path(r"^(?P<slug>[\w-]+)\.png$", share_card, name="share_card"),
]
