# Generated manually for P10 cross-project dependencies

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0010_project_change_requests"),
        ("workspaces", "0008_crm_finance_deep_and_roles"),
    ]

    operations = [
        migrations.CreateModel(
            name="CrossProjectDependency",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "dependency_type",
                    models.CharField(
                        choices=[
                            ("FS", "Finish-Start"),
                            ("SS", "Start-Start"),
                            ("FF", "Finish-Finish"),
                            ("SF", "Start-Finish"),
                        ],
                        default="FS",
                        max_length=2,
                    ),
                ),
                ("lag_days", models.IntegerField(default=0)),
                ("note", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "predecessor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cross_successor_links",
                        to="projects.scheduleactivity",
                    ),
                ),
                (
                    "successor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cross_predecessor_links",
                        to="projects.scheduleactivity",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cross_project_dependencies",
                        to="workspaces.workspace",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="crossprojectdependency",
            constraint=models.UniqueConstraint(
                fields=("predecessor", "successor"), name="uniq_cross_project_dep"
            ),
        ),
    ]
