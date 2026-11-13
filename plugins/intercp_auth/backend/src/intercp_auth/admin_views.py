from django.contrib.auth import get_user_model
from django.db import transaction

from drf_spectacular.utils import extend_schema
from loguru import logger
from rest_framework import serializers
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from baserow.api.admin.users.views import UsersAdminView
from baserow.api.admin.views import AdminListingView
from baserow.api.decorators import validate_body
from baserow.core.handler import CoreHandler
from baserow.core.models import (
    WORKSPACE_USER_PERMISSION_ADMIN,
    WORKSPACE_USER_PERMISSION_MEMBER,
    Workspace,
    WorkspaceUser,
)


class AddWorkspaceMemberSerializer(serializers.Serializer):
    # Same workspaces as the admin workspace dropdown (WorkspaceOptionsAdminView).
    workspace_id = serializers.PrimaryKeyRelatedField(
        queryset=Workspace.objects.filter(template__isnull=True), source="workspace"
    )
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(is_active=True), source="user"
    )
    permissions = serializers.ChoiceField(
        choices=[WORKSPACE_USER_PERMISSION_MEMBER, WORKSPACE_USER_PERMISSION_ADMIN],
        default=WORKSPACE_USER_PERMISSION_MEMBER,
    )


class AdminActiveUsersView(AdminListingView):
    """
    The active users the add endpoint accepts, listed like core's staff-only users
    listing (api/admin/users/views.py:50-94). Built on the GET-only AdminListingView,
    not on UsersAdminView, which also has the POST that creates password users.
    """

    serializer_class = UsersAdminView.serializer_class
    pagination_class = UsersAdminView.pagination_class
    search_fields = UsersAdminView.search_fields
    sort_field_mapping = UsersAdminView.sort_field_mapping

    def get_queryset(self, request):
        return UsersAdminView().get_queryset(request).filter(is_active=True)

    @extend_schema(
        tags=["Admin"],
        operation_id="intercp_admin_list_active_users",
        description="Lists the active users, if the requesting user is staff.",
        **AdminListingView.get_extend_schema_parameters(
            "users", serializer_class, search_fields, sort_field_mapping
        ),
    )
    def get(self, request):
        return super().get(request)


class AdminAddWorkspaceMemberView(APIView):
    """Lets a staff member add any active user to any workspace, without an invite."""

    permission_classes = (IsAdminUser,)

    @extend_schema(
        tags=["Admin"],
        operation_id="intercp_admin_add_workspace_member",
        request=AddWorkspaceMemberSerializer,
        description="Adds a user to a workspace. An existing member keeps their role.",
    )
    @transaction.atomic
    @validate_body(AddWorkspaceMemberSerializer, return_validated=True)
    def post(self, request, data):
        workspace, user = data["workspace"], data["user"]
        # Core's add_user_to_workspace doesn't say whether it created the member
        # (core/handler.py:1587-1604), so it's looked up first. The row lock makes
        # concurrent adds to this workspace wait, so a double click gets "already
        # a member" instead of a second "added".
        Workspace.objects.select_for_update().filter(pk=workspace.pk).first()
        existing = WorkspaceUser.objects.filter(workspace=workspace, user=user).first()
        workspace_user = existing or CoreHandler().add_user_to_workspace(
            workspace, user, permissions=data["permissions"]
        )
        if existing is None:
            logger.info(
                f"Staff {request.user.id} added user {user.id} to workspace "
                f"{workspace.id} as {data['permissions']}."
            )
        return Response(
            {
                "workspace_id": workspace.id,
                "user_id": user.id,
                "permissions": workspace_user.permissions,
                "added": existing is None,
            }
        )
