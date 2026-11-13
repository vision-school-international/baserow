import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("database", "0229_remove_view_show_logo_allow_public_export"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GoogleSheetsDataSync",
            fields=[
                (
                    "datasync_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="database.datasync",
                    ),
                ),
                (
                    "google_service_account_key",
                    models.TextField(
                        help_text="The JSON key of the Google service account the "
                        "sheet is shared with. Write only."
                    ),
                ),
                (
                    "google_spreadsheet_id",
                    models.CharField(
                        help_text="The spreadsheet ID or its URL.", max_length=2000
                    ),
                ),
                (
                    "google_sheet_name",
                    models.CharField(
                        help_text="The name of the tab in the spreadsheet.",
                        max_length=255,
                    ),
                ),
                (
                    "google_id_column",
                    models.CharField(
                        help_text="The header of the column that holds a unique ID "
                        "for every row.",
                        max_length=255,
                    ),
                ),
                (
                    "authorized_user",
                    models.ForeignKey(
                        help_text="The user on whose behalf the periodic sync runs.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            bases=("database.datasync",),
        ),
    ]
