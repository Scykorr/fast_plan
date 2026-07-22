"""Celery tasks for CRM automations."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("fast_plan")


@shared_task(name="crm.run_daily_automations")
def run_daily_automations() -> dict:
    from crm.automation import run_schedule_daily_automations

    stats = run_schedule_daily_automations()
    logger.info("crm.run_daily_automations finished: %s", stats)
    return stats


@shared_task(name="crm.sync_channels")
def sync_channels() -> dict:
    from crm.channels import sync_all_active_connections

    stats = sync_all_active_connections()
    logger.info("crm.sync_channels finished: %s", stats)
    return stats
