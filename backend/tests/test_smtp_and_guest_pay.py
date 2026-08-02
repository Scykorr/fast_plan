"""SMTP status / test-send and guest payment status."""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core import mail
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import CrmDocument, CrmDocumentPayment


@pytest.mark.django_db
def test_email_status_owner_only(authenticated_client, workspace, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.EMAIL_HOST = "smtp.example.com"
    settings.EMAIL_PORT = 587
    settings.EMAIL_HOST_USER = "mailer"
    settings.REQUIRE_EMAIL_VERIFICATION = False

    ok = authenticated_client.get("/api/workspace/email/status/")
    assert ok.status_code == status.HTTP_200_OK
    assert ok.data["backend"].endswith("locmem.EmailBackend")
    assert ok.data["host"] == "smtp.example.com"
    assert ok.data["host_user_set"] is True
    assert ok.data["require_email_verification"] is False
    assert "password" not in ok.data

    # API token cannot manage email
    token = authenticated_client.post(
        "/api/workspace/api-tokens/",
        {"name": "Bot", "scopes": ["read", "write"]},
        format="json",
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.data['token']}")
    denied = client.get("/api/workspace/email/status/")
    assert denied.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_email_test_send_locmem(authenticated_client, workspace, user, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    mail.outbox.clear()

    response = authenticated_client.post(
        "/api/workspace/email/test/",
        {},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["ok"] is True
    assert response.data["to"] == user.email
    assert len(mail.outbox) == 1
    assert "тест SMTP" in mail.outbox[0].subject


@pytest.mark.django_db
def test_email_test_send_reports_failure(authenticated_client, workspace, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    with patch(
        "workspaces.email_views.send_app_email_result",
        return_value=(False, "SMTP refused"),
    ):
        response = authenticated_client.post(
            "/api/workspace/email/test/",
            {"to": "ops@example.com"},
            format="json",
        )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["ok"] is False
    assert response.data["detail"] == "SMTP refused"
    assert response.data["to"] == "ops@example.com"


@pytest.mark.django_db
def test_guest_share_payment_status(authenticated_client, workspace, user):
    doc = CrmDocument.objects.create(
        workspace=workspace,
        doc_type=CrmDocument.DocType.INVOICE,
        title="Invoice Pay",
        number="I-1",
        status=CrmDocument.Status.ACCEPTED,
        amount=Decimal("1000.00"),
        currency="RUB",
        created_by=user,
    )
    create_link = authenticated_client.post(
        f"/api/crm/documents/{doc.id}/share-links/",
        {"label": "Pay", "allow_approve": False, "allow_pdf": True},
        format="json",
    )
    token = create_link.data["token"]
    guest = APIClient()

    unpaid = guest.get(f"/api/crm/share/{token}/")
    assert unpaid.status_code == status.HTTP_200_OK
    assert unpaid.data["document"]["payment_status"] == "unpaid"
    assert unpaid.data["document"]["balance_due"] == "1000.00"
    assert unpaid.data["document"]["payments"] == []

    CrmDocumentPayment.objects.create(
        document=doc,
        amount=Decimal("400.00"),
        paid_at="2026-08-01",
    )
    partial = guest.get(f"/api/crm/share/{token}/")
    assert partial.data["document"]["payment_status"] == "partial"
    assert partial.data["document"]["paid_total"] == "400.00"
    assert partial.data["document"]["balance_due"] == "600.00"
    assert len(partial.data["document"]["payments"]) == 1

    CrmDocumentPayment.objects.create(
        document=doc,
        amount=Decimal("600.00"),
        paid_at="2026-08-02",
    )
    paid = guest.get(f"/api/crm/share/{token}/")
    assert paid.data["document"]["payment_status"] == "paid"
    assert paid.data["document"]["balance_due"] == "0.00"
    assert len(paid.data["document"]["payments"]) == 2
