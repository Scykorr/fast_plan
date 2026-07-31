# Generated manually for P10 sprint 2

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("process", "0001_p8_process_bpmn_dmn_cmmn"),
        ("projects", "0009_p6a_crm_foundation"),
    ]

    operations = [
        migrations.AddField(
            model_name="usertask",
            name="wbs_node",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional bind to a WBS work package; completed on task complete.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="process_user_tasks",
                to="projects.wbsnode",
            ),
        ),
    ]
