"""Ladya Hub workspace defaults."""

from __future__ import annotations

from django.conf import settings

from ladya.models import LadyaSettings


def ladya_hub_enabled_default() -> bool:
    return bool(getattr(settings, "LADYA_HUB_ENABLED_DEFAULT", False))


def get_or_create_ladya_settings(workspace) -> tuple[LadyaSettings, bool]:
    return LadyaSettings.objects.get_or_create(
        workspace=workspace,
        defaults={"ladya_hub_enabled": ladya_hub_enabled_default()},
    )
