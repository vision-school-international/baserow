from django.db import transaction

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from baserow.api.decorators import map_exceptions, validate_body
from baserow.api.errors import ERROR_GROUP_DOES_NOT_EXIST, ERROR_USER_NOT_IN_GROUP
from baserow.api.jobs.errors import ERROR_JOB_DOES_NOT_EXIST
from baserow.contrib.database.api.fields.errors import (
    ERROR_FIELD_DOES_NOT_EXIST,
    ERROR_INCOMPATIBLE_FIELD,
)
from baserow.contrib.database.fields.exceptions import (
    FieldDoesNotExist,
    IncompatibleField,
)
from baserow.core.exceptions import UserNotInWorkspace, WorkspaceDoesNotExist
from baserow.core.jobs.constants import JOB_FINISHED
from baserow.core.jobs.exceptions import JobDoesNotExist

from .handler import AIPromptHandler
from .job_types import TransformAICellsJobType
from .models import TransformAICellsJob


class TransformNotApplicable(Exception):
    """The job hasn't finished, or its proposals were applied already."""


ERROR_TRANSFORM_NOT_APPLICABLE = (
    "ERROR_TRANSFORM_NOT_APPLICABLE",
    HTTP_400_BAD_REQUEST,
    "These changes can't be applied: the AI hasn't finished, or they were "
    "applied already.",
)


class CellSerializer(serializers.Serializer):
    row_id = serializers.IntegerField()
    field_id = serializers.IntegerField()


class ApplyTransformSerializer(serializers.Serializer):
    cells = serializers.ListField(
        child=CellSerializer(),
        help_text="The proposals to write, by row and field. The others are rejected.",
    )


class ApplyTransformView(APIView):
    """
    Writes the accepted proposals of the user's finished transform job, once. Each
    cell is written only if it hasn't changed since the model read it.
    """

    permission_classes = (IsAuthenticated,)

    @map_exceptions(
        {
            JobDoesNotExist: ERROR_JOB_DOES_NOT_EXIST,
            TransformNotApplicable: ERROR_TRANSFORM_NOT_APPLICABLE,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
            WorkspaceDoesNotExist: ERROR_GROUP_DOES_NOT_EXIST,
            FieldDoesNotExist: ERROR_FIELD_DOES_NOT_EXIST,
            IncompatibleField: ERROR_INCOMPATIBLE_FIELD,
        }
    )
    @validate_body(ApplyTransformSerializer)
    @transaction.atomic
    def post(self, request, job_id, data):
        # Locked, so two applies of the same job can't both write.
        job = (
            TransformAICellsJob.objects.select_for_update()
            .filter(id=job_id, user=request.user)
            .first()
        )
        if job is None:
            raise JobDoesNotExist(f"The job {job_id} does not exist.")
        if job.state != JOB_FINISHED or job.applied:
            raise TransformNotApplicable()

        # Checked again: the fields or the user's access may have changed.
        fields = TransformAICellsJobType()._get_fields_or_raise(
            request.user, job.field_ids or [job.field_id]
        )
        accepted = {(cell["row_id"], cell["field_id"]) for cell in data["cells"]}
        written, skipped = AIPromptHandler().apply_cells(
            request.user, job, fields, accepted
        )
        job.applied = True
        job.save(update_fields=["applied"])
        return Response({"written": written, "skipped_row_ids": skipped})
