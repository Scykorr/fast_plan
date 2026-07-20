"""Create or refresh user/project/share-link fixtures for staging smoke checks."""

import json
import os
import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from projects.models import Project, ProjectShareLink
from workspaces.models import Workspace
from workspaces.services import set_active_workspace

User = get_user_model()

DEFAULT_EMAIL = "smoke@fast-plan.ci"
DEFAULT_PASSWORD = "smokepass123"
DEFAULT_PROJECT_NAME = "Smoke Test Project"


class Command(BaseCommand):
    help = "Create or refresh CI/staging smoke test fixtures (user, project, share link)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print fixture metadata as JSON on stdout.",
        )

    def handle(self, *args, **options):
        email = os.environ.get("SMOKE_USER_EMAIL", DEFAULT_EMAIL)
        password = os.environ.get("SMOKE_USER_PASSWORD", DEFAULT_PASSWORD)
        project_name = os.environ.get("SMOKE_PROJECT_NAME", DEFAULT_PROJECT_NAME)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email.split("@", 1)[0].replace(".", "_")[:30],
                "email_verified_at": timezone.now(),
            },
        )
        user.set_password(password)
        user.email_verified_at = timezone.now()
        user.save(update_fields=["password", "email_verified_at"])

        workspace = user.active_workspace or Workspace.objects.filter(owner=user).first()
        if workspace is None:
            workspace = Workspace.objects.create(name="Smoke Workspace", owner=user)
        set_active_workspace(user, workspace)

        project = (
            Project.objects.filter(workspace=workspace, name=project_name)
            .order_by("id")
            .first()
        )
        if project is None:
            project = Project.objects.create(
                workspace=workspace,
                name=project_name,
                description="Automated smoke-check fixtures",
                manager=user,
            )

        link = (
            ProjectShareLink.objects.filter(project=project, revoked_at__isnull=True)
            .order_by("id")
            .first()
        )
        if link is None:
            link = ProjectShareLink.objects.create(
                project=project,
                token=secrets.token_urlsafe(24),
                label="Smoke check",
                created_by=user,
            )

        payload = {
            "email": email,
            "password": password,
            "workspace_id": workspace.id,
            "project_id": project.id,
            "share_token": link.token,
            "created_user": created,
        }
        if options["json"]:
            self.stdout.write(json.dumps(payload))
        else:
            self.stdout.write(json.dumps(payload, indent=2))
