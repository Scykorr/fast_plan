# Migration generated for Agent Ops default-on.

from django.db import migrations, models


def enable_agent_ops_for_existing_workspaces(apps, schema_editor):
    DeliverySettings = apps.get_model("delivery", "DeliverySettings")
    Workspace = apps.get_model("workspaces", "Workspace")
    DeliverySettings.objects.all().update(agent_ops_enabled=True)
    existing = set(
        DeliverySettings.objects.values_list("workspace_id", flat=True)
    )
    for workspace_id in Workspace.objects.values_list("id", flat=True):
        if workspace_id not in existing:
            DeliverySettings.objects.create(
                workspace_id=workspace_id,
                agent_ops_enabled=True,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0007_agent_auto_claim"),
    ]

    operations = [
        migrations.AlterField(
            model_name="deliverysettings",
            name="agent_ops_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(
            enable_agent_ops_for_existing_workspaces,
            migrations.RunPython.noop,
        ),
    ]
