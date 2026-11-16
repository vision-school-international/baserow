from django.db import transaction

from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from baserow.api.decorators import map_exceptions, validate_body
from baserow.api.errors import ERROR_USER_NOT_IN_GROUP
from baserow.contrib.database.api.views.errors import ERROR_VIEW_DOES_NOT_EXIST
from baserow.contrib.database.api.views.form.errors import (
    ERROR_FORM_DOES_NOT_EXIST,
    ERROR_NO_PERMISSION_TO_PUBLICLY_SHARED_FORM,
)
from baserow.contrib.database.api.views.utils import (
    get_public_view_authorization_token,
)
from baserow.contrib.database.views.exceptions import (
    NoAuthorizationToPubliclySharedView,
    ViewDoesNotExist,
)
from baserow.contrib.database.views.handler import ViewHandler
from baserow.contrib.database.views.models import FormView
from baserow.core.exceptions import UserNotInWorkspace

from .form_view_mode_types import FormWithRowsModeType
from .handler import InvalidListView, get_settings, list_payload, update_settings

ERROR_FORM_ROWS_INVALID_VIEW = (
    "ERROR_FORM_ROWS_INVALID_VIEW",
    HTTP_400_BAD_REQUEST,
    "The rows must come from a view of the form's table that lists rows.",
)


class SettingsSerializer(serializers.Serializer):
    list_view_id = serializers.IntegerField(required=False, allow_null=True)
    heading = serializers.CharField(max_length=255, required=False, allow_blank=True)
    intro = serializers.CharField(max_length=500, required=False, allow_blank=True)
    allow_edit = serializers.BooleanField(required=False)


def _editor_response(form):
    settings = get_settings(form)
    return Response(
        {
            "list_view_id": settings.list_view_id,
            "heading": settings.heading,
            "intro": settings.intro,
            "allow_edit": settings.allow_edit,
            "edit_field_id": settings.edit_field_id,
            "list": list_payload(form),
        }
    )


class FormRowsSettingsView(APIView):
    """The form editor's settings and list preview (any form the user can read)."""

    @map_exceptions(
        {
            ViewDoesNotExist: ERROR_VIEW_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
        }
    )
    def get(self, request, view_id):
        form = ViewHandler().get_view_as_user(request.user, view_id, FormView)
        return _editor_response(form)

    @transaction.atomic
    @map_exceptions(
        {
            ViewDoesNotExist: ERROR_VIEW_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
            InvalidListView: ERROR_FORM_ROWS_INVALID_VIEW,
        }
    )
    @validate_body(SettingsSerializer)
    def patch(self, request, data, view_id):
        form = ViewHandler().get_view_as_user(request.user, view_id, FormView)
        update_settings(request.user, form, data)
        return _editor_response(form)


class PublicFormRowsView(APIView):
    """The list on the public form, checked like the form itself."""

    permission_classes = (AllowAny,)

    @map_exceptions(
        {
            ViewDoesNotExist: ERROR_FORM_DOES_NOT_EXIST,
            NoAuthorizationToPubliclySharedView: (
                ERROR_NO_PERMISSION_TO_PUBLICLY_SHARED_FORM
            ),
        }
    )
    def get(self, request, slug):
        # Same lookup as the public form's own endpoint (api/views/form/views.py).
        form = ViewHandler().get_public_view_by_slug(
            request.user,
            slug,
            view_model=FormView,
            authorization_token=get_public_view_authorization_token(request),
        )
        if form.mode != FormWithRowsModeType.type:
            raise ViewDoesNotExist()
        return Response(list_payload(form))
