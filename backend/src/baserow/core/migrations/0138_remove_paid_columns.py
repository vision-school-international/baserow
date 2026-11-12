from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0137_mcpendpoint_rename_create_dashboards"),
    ]

    operations = [
        migrations.RemoveField(model_name="settings", name="co_branding_logo"),
        migrations.RemoveField(model_name="workspace", name="seats_taken"),
        migrations.RemoveField(model_name="workspace", name="seats_taken_updated_at"),
    ]
