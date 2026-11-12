from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0006_dashboard_sharing"),
    ]

    operations = [
        migrations.RemoveField(model_name="dashboard", name="show_logo"),
    ]
