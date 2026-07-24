"""CRM calendar events + Outlook/Google sync (mocked)."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from crm.models import (
    Activity,
    CalendarConnection,
    Deal,
    DealTask,
    Organization,
)
from crm.services import ensure_default_pipeline


@pytest.fixture
def deal_with_task(workspace, user):
    pipeline = ensure_default_pipeline(workspace)
    org = Organization.objects.create(workspace=workspace, name="Acme")
    deal = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=pipeline.stages.first(),
        title="Big deal",
        organization=org,
        owner=user,
        close_date=timezone.localdate() + timedelta(days=3),
    )
    task = DealTask.objects.create(
        deal=deal,
        title="Call client",
        due_date=timezone.localdate() + timedelta(days=1),
    )
    Activity.objects.create(
        workspace=workspace,
        kind=Activity.Kind.MEETING,
        subject="Kickoff",
        occurred_at=timezone.now() + timedelta(days=2),
        organization=org,
        deal=deal,
        created_by=user,
    )
    return deal, task


@pytest.mark.django_db
def test_crm_calendar_events(authenticated_client, deal_with_task):
    deal, task = deal_with_task
    today = timezone.localdate()
    response = authenticated_client.get(
        f"/api/calendar/crm/?year={today.year}&month={today.month}"
    )
    assert response.status_code == status.HTTP_200_OK
    ids = {row["id"] for row in response.data}
    assert f"deal-task-{task.id}" in ids
    assert f"deal-close-{deal.id}" in ids
    assert any(row["extendedProps"]["event_type"] == "meeting" for row in response.data)


@pytest.mark.django_db
def test_calendar_providers_and_sync_mock(authenticated_client, workspace, user, deal_with_task):
    listed = authenticated_client.get("/api/crm/calendar/providers/")
    assert listed.status_code == status.HTTP_200_OK
    assert "microsoft" in listed.data

    connection = CalendarConnection.objects.create(
        workspace=workspace,
        user=user,
        provider=CalendarConnection.Provider.MICROSOFT,
        refresh_token="refresh",
        access_token="access",
        token_expires_at=timezone.now() + timedelta(hours=1),
    )

    def fake_upsert(conn, access, payload):
        return f"ext-{payload['source_type']}-{payload['source_id']}"

    with patch("crm.calendar_sync.ensure_access_token", return_value="access"):
        with patch("crm.calendar_sync._upsert_external", side_effect=fake_upsert):
            sync = authenticated_client.post(
                f"/api/crm/calendar/connections/{connection.id}/sync/",
                {},
                format="json",
            )
    assert sync.status_code == status.HTTP_200_OK
    assert sync.data["ok"] is True
    assert sync.data["pushed"] >= 1
    connection.refresh_from_db()
    assert connection.last_synced_at is not None
