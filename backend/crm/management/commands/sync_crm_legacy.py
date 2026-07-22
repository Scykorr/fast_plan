from django.core.management.base import BaseCommand

from crm.services import sync_project_stakeholders, sync_workspace_contacts
from workspaces.models import Workspace
from projects.models import Project


class Command(BaseCommand):
    help = "Import birthday contacts and project stakeholders into CRM directory"

    def add_arguments(self, parser):
        parser.add_argument("--workspace-id", type=int, required=False)

    def handle(self, *args, **options):
        ws_id = options.get("workspace_id")
        workspaces = Workspace.objects.all()
        if ws_id:
            workspaces = workspaces.filter(pk=ws_id)
        total_c = total_s = 0
        for workspace in workspaces:
            c = sync_workspace_contacts(workspace)
            s = 0
            for project in Project.objects.filter(workspace=workspace):
                s += sync_project_stakeholders(project)
            total_c += c
            total_s += s
            self.stdout.write(
                f"workspace={workspace.id}: contacts={c}, stakeholders={s}"
            )
        self.stdout.write(self.style.SUCCESS(f"Done. contacts={total_c} stakeholders={total_s}"))
