"""Delivery / Agent Ops workspace defaults."""

from __future__ import annotations

from django.conf import settings

from delivery.models import DeliverySettings


def agent_ops_enabled_default() -> bool:
    return bool(getattr(settings, "AGENT_OPS_ENABLED_DEFAULT", True))


def get_or_create_delivery_settings(workspace) -> tuple[DeliverySettings, bool]:
    return DeliverySettings.objects.get_or_create(
        workspace=workspace,
        defaults={"agent_ops_enabled": agent_ops_enabled_default()},
    )
