from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0136_template_reject_reason_help_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspaceinvitationlink",
            name="password",
            field=models.CharField(
                blank=True,
                db_default="",
                default="",
                help_text="The hashed password that people must enter before they "
                "can see or use the link. Empty when the link isn't password "
                "protected.",
                max_length=128,
            ),
        ),
    ]
