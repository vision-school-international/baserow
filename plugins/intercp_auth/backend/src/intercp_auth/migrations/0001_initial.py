import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0035_add_auth_providers"),
    ]

    operations = [
        migrations.CreateModel(
            name="InterCPAuthProviderModel",
            fields=[
                (
                    "authprovidermodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="core.authprovidermodel",
                    ),
                ),
            ],
            bases=("core.authprovidermodel",),
        ),
    ]
