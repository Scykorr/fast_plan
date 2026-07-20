import json

import pytest
from django.core.management import call_command

from projects.models import Project, ProjectShareLink


@pytest.mark.django_db
def test_ensure_smoke_fixtures_creates_project_and_share_link(capsys):
    call_command("ensure_smoke_fixtures", "--json")
    output = capsys.readouterr().out.strip()
    payload = json.loads(output)
    assert payload["email"]
    assert payload["password"]
    assert Project.objects.filter(pk=payload["project_id"]).exists()
    assert ProjectShareLink.objects.filter(token=payload["share_token"]).exists()
