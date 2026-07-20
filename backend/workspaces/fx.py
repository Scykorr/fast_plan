"""Workspace currency conversion helpers."""

from __future__ import annotations

from decimal import Decimal

from workspaces.models import ExchangeRate, Workspace


def latest_rates(workspace) -> dict[str, Decimal]:
    """Return latest rate_to_base per currency (excluding workspace base = 1)."""
    base = workspace.currency
    rates: dict[str, Decimal] = {base: Decimal("1")}
    rows = (
        ExchangeRate.objects.filter(workspace=workspace)
        .order_by("currency", "-as_of", "-id")
        .values_list("currency", "rate_to_base")
    )
    seen: set[str] = set()
    for currency, rate in rows:
        if currency in seen:
            continue
        seen.add(currency)
        if currency == base:
            continue
        rates[currency] = Decimal(rate)
    return rates


def convert_from_base(
    amount,
    workspace,
    target_currency: str | None = None,
    *,
    rates: dict[str, Decimal] | None = None,
) -> Decimal:
    """Convert an amount stored in workspace base currency to target currency."""
    value = Decimal(str(amount or 0))
    base = workspace.currency
    target = target_currency or base
    if target == base:
        return value
    rate_map = rates or latest_rates(workspace)
    rate = rate_map.get(target)
    if rate is None or rate <= 0:
        return value
    return (value / rate).quantize(Decimal("0.01"))


def serialize_rates(workspace) -> list[dict]:
    """Latest exchange-rate row per currency for API responses."""
    base = workspace.currency
    rows = list(
        ExchangeRate.objects.filter(workspace=workspace).order_by(
            "currency", "-as_of", "-id"
        )
    )
    seen: set[str] = set()
    payload = []
    for row in rows:
        if row.currency in seen:
            continue
        seen.add(row.currency)
        payload.append(
            {
                "id": row.id,
                "currency": row.currency,
                "rate_to_base": str(row.rate_to_base),
                "as_of": row.as_of.isoformat(),
                "created_at": row.created_at.isoformat(),
            }
        )
    if base not in seen:
        payload.insert(
            0,
            {
                "id": None,
                "currency": base,
                "rate_to_base": "1",
                "as_of": None,
                "created_at": None,
            },
        )
    return payload
