from django.conf import settings
from django.db import migrations
from django.db.migrations.recorder import MigrationRecorder

PAID_APP_LABELS = ("baserow_premium", "baserow_enterprise")
PAID_TABLE_PREFIXES = ("baserow_premium_", "baserow_enterprise_")
# Premium models that set a `db_table` outside their app prefix.
PAID_TABLES_WITHOUT_PREFIX = (
    "database_rowcomment",
    "database_rowcomment_mentions",
    "database_kanbanview",
    "database_kanbanviewfieldoptions",
    "database_calendarview",
    "database_calendarviewfieldoptions",
    "database_timelineview",
    "database_timelineviewfieldoptions",
)
PAID_TRASH_ITEM_TYPES = ("row_comment", "team")
# premium views/decorator_types.py:21,25
PAID_DECORATOR_TYPES = ("left_border_color", "background_color")
# enterprise webhook_event_types.py:31
PAID_WEBHOOK_EVENT_TYPES = ("view.rows_entered",)
# Enterprise vector tables, named database_semantic_search_workspace_<id>_data.
PAID_TABLE_PREFIXES_EXTRA = ("database_semantic_search_",)
# The only roles core knows (core/models.py WorkspaceUser.permissions).
CORE_ROLES = ("ADMIN", "MEMBER")
PAID_NOTIFICATION_TYPES = (
    "row_comment_mention",
    "row_comment",
    "periodic_data_sync_deactivated",
    "two_way_sync_update_failed",
    "two_way_sync_deactivated",
    "data_scan_new_results",
    "application_user_limit",
)


def delete_paid_data(apps, schema_editor):
    """
    Removes everything the premium and enterprise apps left in the database, so
    an instance that runs with `BASEROW_OSS_ONLY` has no rows whose type it can't
    load. Does nothing otherwise, and nothing when run again.

    Order: the paid tables go first, with CASCADE, because their foreign keys to
    core rows are deferrable without a database cascade and would make deleting
    those core rows fail at commit. Then the core rows of a paid content type are
    deleted through the historical models, so the cascades Django defines for
    their core children run. Only then can the paid content types themselves go,
    with nothing left that points at them through `on_delete=SET(...)`.
    """

    if not settings.BASEROW_OSS_ONLY:
        return

    connection = schema_editor.connection
    alias = connection.alias

    with connection.cursor() as cursor:
        paid_tables = [
            name
            for name in connection.introspection.table_names(cursor)
            if name.startswith(PAID_TABLE_PREFIXES + PAID_TABLE_PREFIXES_EXTRA)
            or name in PAID_TABLES_WITHOUT_PREFIX
        ]
        for name in paid_tables:
            cursor.execute(
                f"DROP TABLE IF EXISTS {schema_editor.quote_name(name)} CASCADE"
            )

    ContentType = apps.get_model("contenttypes", "ContentType")
    paid_content_types = ContentType.objects.using(alias).filter(
        app_label__in=PAID_APP_LABELS
    )

    # DataSync.table (related_name "data_sync") keeps the synced table; unlock its
    # fields (fields/models.py:178-189) before the paid sync rows are deleted.
    apps.get_model("database", "Field")._base_manager.using(alias).filter(
        table__data_sync__content_type__in=paid_content_types
    ).update(read_only=False, immutable_type=False, immutable_properties=False)

    # Personal views were only hidden by the premium permission manager.
    apps.get_model("database", "View")._base_manager.using(alias).exclude(
        ownership_type="collaborative"
    ).delete()
    apps.get_model("database", "ViewDecoration")._base_manager.using(alias).filter(
        type__in=PAID_DECORATOR_TYPES
    ).delete()
    apps.get_model("database", "TableWebhookEvent")._base_manager.using(
        alias
    ).filter(event_type__in=PAID_WEBHOOK_EVENT_TYPES).delete()

    # Core treats every role other than ADMIN as full MEMBER access, so an
    # enterprise role (VIEWER, NO_ACCESS, ...) loses access instead of widening.
    for model_name in (
        "WorkspaceUser",
        "WorkspaceInvitation",
        "WorkspaceInvitationLink",
    ):
        apps.get_model("core", model_name)._base_manager.using(alias).exclude(
            permissions__in=CORE_ROLES
        ).delete()

    for model in apps.get_models():
        for field in model._meta.concrete_fields:
            if (
                field.many_to_one
                # An inherited field is handled on the model that defines it.
                and field.model is model
                and field.related_model._meta.label_lower
                == "contenttypes.contenttype"
            ):
                model._base_manager.using(alias).filter(
                    **{f"{field.name}__in": paid_content_types}
                ).delete()

    apps.get_model("core", "TrashEntry")._base_manager.using(alias).filter(
        trash_item_type__in=PAID_TRASH_ITEM_TYPES
    ).delete()
    apps.get_model("core", "Notification")._base_manager.using(alias).filter(
        type__in=PAID_NOTIFICATION_TYPES
    ).delete()

    paid_content_types.delete()
    MigrationRecorder.Migration.objects.using(alias).filter(
        app__in=PAID_APP_LABELS
    ).delete()


class Migration(migrations.Migration):
    # Every app whose models can point at a deleted row is in the historical
    # state, so the deletions above cascade to all of them.
    dependencies = [
        ("core", "0138_remove_paid_columns"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "__latest__"),
        ("database", "0229_remove_view_show_logo_allow_public_export"),
        ("integrations", "0041_mcp_server_integration"),
        ("builder", "0082_builder_untrusted_content"),
        ("dashboard", "0007_remove_dashboard_show_logo"),
        ("automation", "0043_wait_node_waiting_index"),
        ("agent", "0012_agent_tool_approval_tool_key"),
        ("ws", "0003_realtime_event_history"),
    ]

    operations = [
        migrations.RunPython(delete_paid_data, migrations.RunPython.noop),
    ]
