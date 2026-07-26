"""CRM finance deep (6) + roles expand (9)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from crm.models import CrmDocument, CrmDocumentPayment, Deal, Organization
from crm.services import ensure_default_pipeline
from finance.models import Transaction
from workspaces.models import WorkspaceMember


@pytest.fixture
def org(workspace):
    return Organization.objects.create(workspace=workspace, name="Acme Corp")


@pytest.fixture
def deal(workspace, user, org):
    pipeline = ensure_default_pipeline(workspace)
    stage = pipeline.stages.first()
    return Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=stage,
        title="Big deal",
        owner=user,
        organization=org,
        amount=Decimal("10000"),
        probability=50,
        close_date=timezone.localdate() + timedelta(days=20),
    )


def test_crm_roles_accounting_marketing(authenticated_client, workspace, user):
    member = WorkspaceMember.objects.get(workspace=workspace, user=user)
    patched = authenticated_client.patch(
        f"/api/workspace/members/{member.id}/",
        {"crm_role": "accounting"},
        format="json",
    )
    assert patched.status_code == 200
    assert patched.data["crm_role"] == "accounting"

    patched = authenticated_client.patch(
        f"/api/workspace/members/{member.id}/",
        {"crm_role": "marketing"},
        format="json",
    )
    assert patched.status_code == 200
    assert patched.data["crm_role"] == "marketing"


def test_ar_ap_bill_and_payment_links_finance(
    authenticated_client, workspace, org, deal
):
    invoice = authenticated_client.post(
        "/api/crm/documents/",
        {
            "doc_type": "invoice",
            "title": "Invoice 1",
            "amount": "1000.00",
            "status": "sent",
            "due_date": str(timezone.localdate() + timedelta(days=10)),
            "organization_id": org.id,
            "deal_id": deal.id,
        },
        format="json",
    )
    assert invoice.status_code == 201

    bill = authenticated_client.post(
        "/api/crm/documents/",
        {
            "doc_type": "bill",
            "title": "Vendor bill",
            "amount": "400.00",
            "status": "sent",
            "due_date": str(timezone.localdate() + timedelta(days=15)),
            "organization_id": org.id,
        },
        format="json",
    )
    assert bill.status_code == 201

    ar_ap = authenticated_client.get("/api/crm/ar-ap/")
    assert ar_ap.status_code == 200
    assert ar_ap.data["ar_open_amount"] == 1000.0
    assert ar_ap.data["ap_open_amount"] == 400.0
    assert ar_ap.data["ap_open_count"] == 1

    pay = authenticated_client.post(
        f"/api/crm/documents/{invoice.data['id']}/payments/",
        {"amount": "1000.00"},
        format="json",
    )
    assert pay.status_code == 201
    payment = CrmDocumentPayment.objects.get(id=pay.data["id"])
    assert payment.finance_transaction_id is not None
    tx = payment.finance_transaction
    assert tx.transaction_type == Transaction.TransactionType.INCOME
    assert tx.organization_id == org.id
    assert tx.deal_id == deal.id

    pnl = authenticated_client.get("/api/crm/finance/pnl/")
    assert pnl.status_code == 200
    assert pnl.data["income_total"] == 1000.0
    assert any(row["organization_id"] == org.id for row in pnl.data["by_organization"])
    assert any(row["deal_id"] == deal.id for row in pnl.data["by_deal"])

    cf = authenticated_client.get("/api/crm/cashflow-forecast/?days=90")
    assert cf.status_code == 200
    assert len(cf.data["buckets"]) >= 1
    assert cf.data["buckets"][0]["outflow"] >= 400.0
