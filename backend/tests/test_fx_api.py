"""Tests for workspace FX settings and conversion."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from workspaces.fx import convert_from_base, latest_rates
from workspaces.models import ExchangeRate, Workspace
from workspaces.services import set_active_workspace


@pytest.fixture
def owner_client(user, workspace):
    client = APIClient()
    set_active_workspace(user, workspace)
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_WORKSPACE_ID=str(workspace.id))
    return client


@pytest.mark.django_db
def test_get_workspace_settings(owner_client, workspace):
    response = owner_client.get("/api/workspace/settings/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["currency"] == Workspace.Currency.RUB
    assert any(row["currency"] == "RUB" for row in response.data["exchange_rates"])


@pytest.mark.django_db
def test_patch_workspace_currency(owner_client, workspace):
    response = owner_client.patch(
        "/api/workspace/settings/",
        {"currency": "USD"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    workspace.refresh_from_db()
    assert workspace.currency == Workspace.Currency.USD


@pytest.mark.django_db
def test_create_and_delete_exchange_rate(owner_client, workspace):
    created = owner_client.post(
        "/api/workspace/exchange-rates/",
        {
            "currency": "USD",
            "rate_to_base": "90.50000000",
            "as_of": date.today().isoformat(),
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    rate_id = created.data["id"]

    listed = owner_client.get("/api/workspace/exchange-rates/")
    assert listed.status_code == status.HTTP_200_OK
    assert any(row["currency"] == "USD" for row in listed.data)

    deleted = owner_client.delete(f"/api/workspace/exchange-rates/{rate_id}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_convert_from_base_helper(workspace):
    ExchangeRate.objects.create(
        workspace=workspace,
        currency=Workspace.Currency.USD,
        rate_to_base=Decimal("90.5"),
        as_of=date.today(),
    )
    rates = latest_rates(workspace)
    assert rates["USD"] == Decimal("90.5")
    converted = convert_from_base(905, workspace, "USD", rates=rates)
    assert converted == Decimal("10.00")


@pytest.mark.django_db
def test_fx_convert_api(owner_client, workspace):
    ExchangeRate.objects.create(
        workspace=workspace,
        currency=Workspace.Currency.EUR,
        rate_to_base=Decimal("98.0"),
        as_of=date.today(),
    )
    response = owner_client.get("/api/workspace/fx/convert/?amount=980&currency=EUR")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["converted_amount"] == 10.0
    assert response.data["base_currency"] == "RUB"


@pytest.mark.django_db
def test_dashboard_includes_currency(owner_client, workspace):
    response = owner_client.get("/api/workspace/dashboard/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["currency"] == workspace.currency
