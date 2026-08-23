# Generated manually for agent auto-claim

from django.db import migrations, models


def enable_auto_claim_for_service_accounts(apps, schema_editor):
    AgentProfile = apps.get_model("delivery", "AgentProfile")
    AgentProfile.objects.filter(is_service_account=True).update(auto_claim_on_assign=True)


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0006_agent_work_handoff"),
    ]

    operations = [
        migrations.AddField(
            model_name="agentprofile",
            name="auto_claim_on_assign",
            field=models.BooleanField(
                default=False,
                help_text="Service account: automatically claim (in progress) when assigned or handed off.",
            ),
        ),
        migrations.RunPython(
            enable_auto_claim_for_service_accounts,
            migrations.RunPython.noop,
        ),
    ]
