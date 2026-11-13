from django.conf import settings
from django.core.exceptions import ValidationError

from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from baserow.api.decorators import map_exceptions, validate_body
from baserow.contrib.database.api.fields.errors import ERROR_FIELD_DOES_NOT_EXIST
from baserow.contrib.database.api.views.form.errors import (
    ERROR_FORM_DOES_NOT_EXIST,
    ERROR_NO_PERMISSION_TO_PUBLICLY_SHARED_FORM,
)
from baserow.contrib.database.api.views.utils import get_public_view_authorization_token
from baserow.contrib.database.fields.models import Field
from baserow.contrib.database.views.exceptions import (
    NoAuthorizationToPubliclySharedView,
    ViewDoesNotExist,
)
from baserow.contrib.database.views.handler import ViewHandler
from baserow.contrib.database.views.models import FormView
from baserow.contrib.database.views.registries import view_ownership_type_registry

from .models import InternationalPhoneField, PatternTextField

# The fields whose values the form checks while the respondent types.
CHECKED_FIELDS = (PatternTextField, InternationalPhoneField)


class CheckFormValueSerializer(serializers.Serializer):
    # The submit's text limit (database/fields/field_types.py TextFieldType).
    value = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        trim_whitespace=False,
        max_length=settings.MAX_FIELD_TEXT_LENGTH,
    )


class CheckFormValueView(APIView):
    """
    Checks one value of a pattern text or phone field of a form, as submitting would
    (api/views/form/views.py SubmitFormViewView), so the form can show the error
    while the respondent types. Nothing is saved.
    """

    permission_classes = (AllowAny,)

    @map_exceptions(
        {
            ViewDoesNotExist: ERROR_FORM_DOES_NOT_EXIST,
            NoAuthorizationToPubliclySharedView: ERROR_NO_PERMISSION_TO_PUBLICLY_SHARED_FORM,
            Field.DoesNotExist: ERROR_FIELD_DOES_NOT_EXIST,
        }
    )
    @validate_body(CheckFormValueSerializer)
    def post(self, request, slug, field_id, data):
        form = ViewHandler().get_public_view_by_slug(
            request.user,
            slug,
            view_model=FormView,
            authorization_token=get_public_view_authorization_token(request),
        )
        view_ownership_type_registry.get(
            form.ownership_type
        ).before_form_view_submitted(form, request)
        # Only a field the form asks for, like the fields a submit accepts.
        options = FormView.active_field_options_in(form.table.database.workspace)
        field = Field.objects.get(
            id=field_id,
            id__in=options.filter(form_view=form).values("field_id"),
        ).specific
        if not isinstance(field, CHECKED_FIELDS):
            raise Field.DoesNotExist()

        try:
            # The check a submit runs on the value (prepare_value_for_db).
            field.get_type().prepare_value_for_db(field, data["value"])
        except ValidationError as exc:
            return Response({"valid": False, "error": exc.messages[0]})
        return Response({"valid": True, "error": None})
