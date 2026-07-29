"""CRM calendar events + Outlook/Google sync (mocked)."""

from datetime import datetime, time, timedelta
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
    today = timezone.localdate()
    # Stay in the current calendar month AND inside the sync horizon
    # (push uses roughly now-7d .. now+90d). Prefer tomorrow when possible.
    from calendar import monthrange

    last = monthrange(today.year, today.month)[1]
    anchor = today if today.day >= last else today + timedelta(days=1)
    deal = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=pipeline.stages.first(),
        title="Big deal",
        organization=org,
        owner=user,
        close_date=anchor,
    )
    task = DealTask.objects.create(
        deal=deal,
        title="Call client",
        due_date=anchor,
    )
    Activity.objects.create(
        workspace=workspace,
        kind=Activity.Kind.MEETING,
        subject="Kickoff",
        occurred_at=timezone.make_aware(datetime.combine(anchor, time(12, 0))),
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
        return {
            "id": f"ext-{payload['source_type']}-{payload['source_id']}",
            "etag": "etag-1",
            "updated": timezone.now().isoformat(),
        }

    with patch("crm.calendar_sync.ensure_access_token", return_value="access"):
        with patch("crm.calendar_sync._upsert_external", side_effect=fake_upsert):
            with patch("crm.calendar_sync.list_external_events", return_value=[]):
                sync = authenticated_client.post(
                    f"/api/crm/calendar/connections/{connection.id}/sync/",
                    {"direction": "both"},
                    format="json",
                )
    assert sync.status_code == status.HTTP_200_OK
    assert sync.data["ok"] is True
    assert sync.data["pushed"] >= 1
    connection.refresh_from_db()
    assert connection.last_synced_at is not None


@pytest.mark.django_db
def test_calendar_pull_imports_external_meeting(
    authenticated_client, workspace, user
):
    connection = CalendarConnection.objects.create(
        workspace=workspace,
        user=user,
        provider=CalendarConnection.Provider.GOOGLE,
        refresh_token="refresh",
        access_token="access",
        token_expires_at=timezone.now() + timedelta(hours=1),
        conflict_policy=CalendarConnection.ConflictPolicy.THEIRS,
    )
    start = timezone.now() + timedelta(days=1)
    external = [
        {
            "id": "g-ext-1",
            "etag": "e1",
            "title": "External sync meet",
            "body": "from google",
            "start": start,
            "updated": start,
        }
    ]
    with patch("crm.calendar_sync.ensure_access_token", return_value="access"):
        with patch("crm.calendar_sync.list_external_events", return_value=external):
            with patch("crm.calendar_sync._upsert_external") as upsert:
                pull = authenticated_client.post(
                    f"/api/crm/calendar/connections/{connection.id}/sync/",
                    {"direction": "pull"},
                    format="json",
                )
                upsert.assert_not_called()
    assert pull.status_code == status.HTTP_200_OK
    assert pull.data["ok"] is True
    assert pull.data["imported"] >= 1
    assert Activity.objects.filter(
        workspace=workspace,
        subject="External sync meet",
        channel=Activity.Channel.CALENDAR,
    ).exists()


@pytest.mark.django_db
def test_calendar_conflict_policy_patch_and_resolve(
    authenticated_client, workspace, user
):
    from crm.models import CalendarEventLink, CalendarSyncConflict

    connection = CalendarConnection.objects.create(
        workspace=workspace,
        user=user,
        provider=CalendarConnection.Provider.MICROSOFT,
        refresh_token="refresh",
        access_token="access",
        conflict_policy=CalendarConnection.ConflictPolicy.OURS,
    )
    patched = authenticated_client.patch(
        f"/api/crm/calendar/connections/{connection.id}/",
        {"conflict_policy": "manual"},
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK
    assert patched.data["conflict_policy"] == "manual"

    link = CalendarEventLink.objects.create(
        connection=connection,
        source_type="meeting",
        source_id="1",
        external_event_id="ext-c1",
    )
    conflict = CalendarSyncConflict.objects.create(
        connection=connection,
        link=link,
        external_event_id="ext-c1",
        local_title="Local",
        external_title="Remote",
    )
    listed = authenticated_client.get("/api/crm/calendar/conflicts/")
    assert listed.status_code == status.HTTP_200_OK
    assert any(row["id"] == conflict.id for row in listed.data)

    resolved = authenticated_client.post(
        f"/api/crm/calendar/conflicts/{conflict.id}/resolve/",
        {"choice": "dismiss"},
        format="json",
    )
    assert resolved.status_code == status.HTTP_200_OK
    assert resolved.data["status"] == CalendarSyncConflict.Status.DISMISSED
