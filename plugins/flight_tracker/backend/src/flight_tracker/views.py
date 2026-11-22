from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from baserow.api.decorators import map_exceptions, validate_query_parameters
from baserow.api.errors import ERROR_USER_NOT_IN_GROUP
from baserow.contrib.database.api.fields.errors import ERROR_FIELD_DOES_NOT_EXIST
from baserow.contrib.database.fields.exceptions import FieldDoesNotExist
from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.table.operations import (
    ListRowsDatabaseTableOperationType,
)
from baserow.core.exceptions import UserNotInWorkspace
from baserow.core.handler import CoreHandler

from .flight import refresh, view_max_age
from .models import REFRESH_VIEW, FlightField, FlightTrackerField

MAX_ROWS = 200
# AirLabs calls one view request may make, and how long it may spend on them;
# the rest wait for the next request.
MAX_LOOKUPS = 20
MAX_SECONDS = 8


class RowIdsSerializer(serializers.Serializer):
    row_ids = serializers.RegexField(
        r"^\d+(,\d+)*$", help_text="Comma separated row ids, at most 200."
    )


class FlightStatusView(APIView):
    """
    The live status of the flights in some rows of a flight field, for the cells
    on screen. Fields set to refresh when viewed look up statuses older than
    FLIGHT_TRACKER_VIEW_TTL_MINUTES; scheduled ones only look up new or changed
    flights, the schedule (tasks.py) refreshes the rest.
    """

    @map_exceptions(
        {
            FieldDoesNotExist: ERROR_FIELD_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
        }
    )
    @validate_query_parameters(RowIdsSerializer)
    def get(self, request, field_id, query_params):
        field = FieldHandler().get_field(field_id, FlightField)
        table = field.table
        # get_field skips trashed fields only (fields/handler.py get_field).
        if table.trashed or table.database.trashed or table.database.workspace.trashed:
            raise FieldDoesNotExist()
        # Reading statuses is reading the rows (api/rows/views.py RowsView.get).
        CoreHandler().check_permissions(
            request.user,
            ListRowsDatabaseTableOperationType.type,
            workspace=table.database.workspace,
            context=table,
        )

        row_ids = list(dict.fromkeys(map(int, query_params["row_ids"].split(","))))
        model = table.get_model(fields=[field], field_ids=[])
        flights_by_row = dict(
            model.objects.filter(id__in=row_ids[:MAX_ROWS]).values_list(
                "id", field.db_column
            )
        )
        statuses, error = refresh(
            field,
            flights_by_row,
            max_age=view_max_age() if field.flight_refresh == REFRESH_VIEW else None,
            max_lookups=MAX_LOOKUPS,
            max_seconds=MAX_SECONDS,
        )
        return Response({"statuses": statuses, "error": error})


class FlightTrackerRefreshView(APIView):
    """
    Asks for the flight data of the rows on screen of a flight tracker field. The
    lookups run in the background (tasks.py fill_tracker, bounded and one at a
    time per field) and the cells update live. Fields set to refresh on a
    schedule only fill new or changed flights here.
    """

    @map_exceptions(
        {
            FieldDoesNotExist: ERROR_FIELD_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
        }
    )
    @validate_query_parameters(RowIdsSerializer)
    def post(self, request, field_id, query_params):
        from .tasks import fill_tracker

        field = FieldHandler().get_field(field_id, FlightTrackerField)
        table = field.table
        # Like FlightStatusView; get_field already skips trashed fields.
        if table.trashed or table.database.trashed or table.database.workspace.trashed:
            raise FieldDoesNotExist()
        CoreHandler().check_permissions(
            request.user,
            ListRowsDatabaseTableOperationType.type,
            workspace=table.database.workspace,
            context=table,
        )
        row_ids = list(dict.fromkeys(map(int, query_params["row_ids"].split(","))))
        fill_tracker.delay(field.id, row_ids[:MAX_ROWS], on_screen=True)
        return Response(status=202)
