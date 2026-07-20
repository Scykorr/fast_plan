from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0006_p4_share_roles_fx"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="ai_prompts",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
