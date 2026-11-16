from baserow.contrib.database.api.rows.serializers import (
    RowSerializer,
    get_row_serializer_class,
)
from baserow.contrib.database.api.views.serializers import PublicFieldSerializer
from baserow.contrib.database.fields.field_sortings import serialize_sorts_to_string
from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.fields.models import Field, FormViewEditRowField
from baserow.contrib.database.fields.registries import (
    exclude_field_options_not_allowed_in_public_views,
    field_type_registry,
)
from baserow.contrib.database.fields.utils.row_edit import build_row_edit_url
from baserow.contrib.database.views.exceptions import ViewDoesNotExist
from baserow.contrib.database.views.handler import ViewHandler
from baserow.contrib.database.views.models import GridView
from baserow.contrib.database.views.operations import UpdateViewOperationType
from baserow.contrib.database.views.registries import view_type_registry
from baserow.core.db import specific_iterator
from baserow.core.handler import CoreHandler

from .models import FormRowsSettings

# shortcut: a long table shows its first 200 rows and a "+ N more" line; add
# paging if a form ever needs more.
MAX_ROWS = 200
# Never listed: an edit link column would hand out every row's edit link, and a
# button does nothing outside the grid.
NEVER_LISTED = ("form_view_edit_row", "button")
EMPTY = (None, "", [])


class InvalidListView(Exception):
    """The view isn't a view of the form's table that has rows."""


def get_settings(form):
    """The form's settings; unsaved defaults when it has none yet."""

    try:
        return form.form_rows_settings
    except FormRowsSettings.DoesNotExist:
        return FormRowsSettings(form_view=form)


def _list_view(settings):
    view = settings.list_view
    if view is None or view.trashed or view.table_id != settings.form_view.table_id:
        return None
    view = view.specific
    return view if view_type_registry.get_by_model(view).can_list_rows else None


def _edit_field(settings):
    field = settings.edit_field
    if (
        not settings.allow_edit
        or field is None
        or field.trashed
        or field.form_view_id != settings.form_view_id
    ):
        return None
    return field


def _create_edit_field(user, form):
    """
    The table's edit link field for this form, added if it has none. Core makes
    the per-row links (FormViewEditRowFieldType, fields/utils/row_edit.py).
    """

    existing = FormViewEditRowField.objects.filter(
        table_id=form.table_id, form_view=form, trashed=False
    ).first()
    if existing is not None:
        return existing

    handler = FieldHandler()
    name = handler.find_next_unused_field_name(form.table, ["Edit link"])
    field = handler.create_field(
        user, form.table, "form_view_edit_row", name=name, form_view_id=form.id
    )
    # New fields show in grid views, and public grid shares show this type's links
    # (its can_be_in_public_view is True), so it starts hidden. No user: this is
    # part of the setting change, not the user's own change to each view.
    for grid in GridView.objects.filter(table_id=form.table_id):
        ViewHandler().update_field_options(
            view=grid, field_options={field.id: {"hidden": True}}
        )
    return field


def update_settings(user, form, values):
    CoreHandler().check_permissions(
        user,
        UpdateViewOperationType.type,
        workspace=form.table.database.workspace,
        context=form,
    )
    # Two saves can arrive at once (typing, then clicking the view list): the
    # second waits for the first's row instead of failing on a duplicate.
    settings, _ = FormRowsSettings.objects.select_for_update().get_or_create(
        form_view=form
    )

    if "list_view_id" in values:
        view_id = values["list_view_id"]
        if view_id is None:
            settings.list_view = None
        else:
            # As the user: someone else's personal view can't be picked.
            try:
                view = ViewHandler().get_view_as_user(
                    user, view_id, table_id=form.table_id
                )
            except ViewDoesNotExist as exc:
                raise InvalidListView() from exc
            if (
                view.trashed
                or not view_type_registry.get_by_model(view.specific).can_list_rows
            ):
                raise InvalidListView()
            settings.list_view = view
    for key in ("heading", "intro", "allow_edit"):
        if key in values:
            setattr(settings, key, values[key])
    if settings.allow_edit and _edit_field(settings) is None:
        settings.edit_field = _create_edit_field(user, form)

    settings.save()
    return settings


def list_payload(form):
    """
    The heading, columns and rows the form lists: what a public share of the list
    view would show (get_public_rows_queryset_and_field_ids), except that link
    fields are sent as counts. Lookup, rollup, formula and collaborator columns
    are sent as a public share sends them: the view's editor picks its columns.
    """

    settings = get_settings(form)
    payload = {
        "heading": settings.heading,
        "intro": settings.intro,
        "fields": [],
        "rows": [],
        "more": 0,
    }
    view = _list_view(settings)
    if view is None:
        return payload

    view_type = view_type_registry.get_by_model(view)
    options = exclude_field_options_not_allowed_in_public_views(
        view_type.get_visible_field_options_in_order(view)
    )
    ordered_ids = list(options.values_list("field_id", flat=True))
    fields = [
        field
        for field in specific_iterator(
            Field.objects.filter(id__in=ordered_ids)
            .select_related("content_type")
            .prefetch_related("select_options")
        )
        if field.get_type().type not in NEVER_LISTED
    ]
    fields.sort(key=lambda field: ordered_ids.index(field.id))
    if not fields:
        return payload

    # The view's own sort. The helper only orders when given a string; even ""
    # puts the view's group-bys first (views/handler.py:4157-4184).
    order_by = serialize_sorts_to_string(
        sort for sort in view.viewsort_set.all() if sort.field_id in ordered_ids
    )
    queryset, _, _ = ViewHandler().get_public_rows_queryset_and_field_ids(
        view, order_by=order_by, view_type=view_type
    )
    total = queryset.count()
    rows = list(queryset[:MAX_ROWS])

    serializer = get_row_serializer_class(
        queryset.model,
        RowSerializer,
        is_response=True,
        field_ids=[field.id for field in fields],
    )
    serialized = serializer(rows, many=True).data
    links = {f"field_{f.id}" for f in fields if f.get_type().type == "link_row"}
    edit_field = _edit_field(settings)

    for row, data in zip(rows, serialized):
        values = {key: value for key, value in data.items() if key.startswith("field_")}
        if all(value in EMPTY for value in values.values()):
            continue
        for key in links:
            values[key] = len(values[key] or [])
        edit_url = None
        if edit_field is not None:
            cell = getattr(row, f"field_{edit_field.id}")
            if cell:
                edit_url = build_row_edit_url(str(cell), form, edit_field.id)
        payload["rows"].append({"id": row.id, "values": values, "edit_url": edit_url})

    payload["fields"] = [
        field_type_registry.get_serializer(field, PublicFieldSerializer).data
        for field in fields
    ]
    payload["more"] = max(total - MAX_ROWS, 0)
    return payload
