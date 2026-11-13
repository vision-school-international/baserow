from django.urls import path

from .admin_views import AdminAddWorkspaceMemberView
from .views import CallbackView, LoginView

app_name = "intercp_auth"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("callback/", CallbackView.as_view(), name="callback"),
    path(
        "admin/workspace-members/",
        AdminAddWorkspaceMemberView.as_view(),
        name="admin_add_workspace_member",
    ),
]
