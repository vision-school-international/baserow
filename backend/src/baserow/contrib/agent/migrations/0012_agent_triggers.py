import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import baserow.core.fields
import baserow.core.formula.field


class Migration(migrations.Migration):
    dependencies = [
        ("agent", "0011_agent_reply_details"),
        ("core", "0135_workspaceinvitationlink_scope"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="agentconversation",
            name="owner_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="agent_conversations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="agentmessage",
            name="role",
            field=models.CharField(
                choices=[
                    ("user", "User"),
                    ("assistant", "Assistant"),
                    ("trigger", "Trigger"),
                ],
                db_default="user",
                default="user",
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="AgentTrigger",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                ("updated_on", baserow.core.fields.SyncedDateTimeField(auto_now=True)),
                ("trashed", models.BooleanField(db_index=True, default=False)),
                ("enabled", models.BooleanField(db_default=True, default=True)),
                (
                    "message",
                    baserow.core.formula.field.FormulaField(
                        blank=True, db_default="", default="", null=True
                    ),
                ),
                (
                    "agent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="triggers",
                        to="agent.agentapplication",
                    ),
                ),
                (
                    "service",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="agent_trigger",
                        to="core.service",
                    ),
                ),
            ],
            options={
                "ordering": ("id",),
            },
        ),
        migrations.AddField(
            model_name="agentconversation",
            name="trigger",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="conversations",
                to="agent.agenttrigger",
            ),
        ),
        migrations.AddIndex(
            model_name="agentconversation",
            index=models.Index(
                fields=["agent", "-updated_on", "-id"],
                name="agent_conversation_shared_idx",
            ),
        ),
    ]
