from django.db import migrations


def seed_all_workspaces(apps, schema_editor):
    Workspace = apps.get_model("workspaces", "Workspace")
    Tracker = apps.get_model("tracking", "Tracker")
    IssueStatus = apps.get_model("tracking", "IssueStatus")
    CustomField = apps.get_model("tracking", "CustomField")
    CustomFieldEnumeration = apps.get_model("tracking", "CustomFieldEnumeration")
    CustomFieldTracker = apps.get_model("tracking", "CustomFieldTracker")

    for workspace in Workspace.objects.all():
        if Tracker.objects.filter(workspace_id=workspace.id).exists():
            continue

        project_tracker = Tracker.objects.create(
            workspace_id=workspace.id,
            name="Проект",
            target="project",
            position=0,
            is_default=True,
        )
        issue_tracker = Tracker.objects.create(
            workspace_id=workspace.id,
            name="Задача",
            target="issue",
            position=1,
            is_default=True,
        )
        Tracker.objects.create(
            workspace_id=workspace.id,
            name="Веха",
            target="issue",
            position=2,
            is_default=False,
        )

        for index, (name, is_closed, is_default) in enumerate(
            (
                ("Новая", False, True),
                ("В работе", False, False),
                ("Решена", False, False),
                ("Закрыта", True, False),
            )
        ):
            IssueStatus.objects.create(
                workspace_id=workspace.id,
                name=name,
                position=index,
                is_closed=is_closed,
                is_default=is_default,
            )

        priority_field = CustomField.objects.create(
            workspace_id=workspace.id,
            name="Приоритет",
            field_format="list",
            position=0,
        )
        for pos, label in enumerate(("Низкий", "Нормальный", "Высокий", "Срочный")):
            CustomFieldEnumeration.objects.create(
                custom_field_id=priority_field.id,
                name=label,
                position=pos,
            )
        CustomFieldTracker.objects.create(
            custom_field_id=priority_field.id,
            tracker_id=issue_tracker.id,
        )

        effort_field = CustomField.objects.create(
            workspace_id=workspace.id,
            name="Оценка (ч)",
            field_format="float",
            position=1,
        )
        CustomFieldTracker.objects.create(
            custom_field_id=effort_field.id,
            tracker_id=issue_tracker.id,
        )

        budget_field = CustomField.objects.create(
            workspace_id=workspace.id,
            name="Бюджетный код",
            field_format="string",
            position=0,
        )
        CustomFieldTracker.objects.create(
            custom_field_id=budget_field.id,
            tracker_id=project_tracker.id,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("tracking", "0001_initial"),
        ("workspaces", "0002_workspaceinvitation"),
    ]

    operations = [
        migrations.RunPython(seed_all_workspaces, migrations.RunPython.noop),
    ]
