from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0228_delete_password_view_default_values"),
    ]

    operations = [
        migrations.RemoveField(model_name="view", name="show_logo"),
        migrations.RemoveField(model_name="view", name="allow_public_export"),
    ]
