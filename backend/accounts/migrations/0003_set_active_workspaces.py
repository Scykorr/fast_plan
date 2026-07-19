from django.db import migrations


def set_active_workspaces(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    WorkspaceMember = apps.get_model("workspaces", "WorkspaceMember")
    for user in User.objects.all():
        if user.active_workspace_id:
            continue
        membership = (
            WorkspaceMember.objects.filter(user=user)
            .select_related("workspace")
            .order_by("workspace__created_at")
            .first()
        )
        if membership:
            user.active_workspace_id = membership.workspace_id
            user.save(update_fields=["active_workspace_id"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_active_workspace"),
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(set_active_workspaces, noop),
    ]
