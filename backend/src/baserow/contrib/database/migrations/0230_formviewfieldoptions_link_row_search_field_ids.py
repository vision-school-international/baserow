from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0229_remove_view_show_logo_allow_public_export"),
    ]

    operations = [
        migrations.AddField(
            model_name="formviewfieldoptions",
            name="link_row_search_field_ids",
            field=models.JSONField(
                db_default=[],
                default=list,
                help_text="For a link row field: the ids of the linked table's fields "
                "that the form's row search also matches, besides the primary field.",
            ),
        ),
    ]
