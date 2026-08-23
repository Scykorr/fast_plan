"""Auto-claim for service accounts and webhook signals for external agent runners."""

from __future__ import annotations

import logging

from delivery.models import AgentProfile, DeliveryTask

logger = logging.getLogger("fast_plan.delivery")


def _task_webhook_payload(
    task: DeliveryTask,
    *,
    auto_claimed: bool,
    source: str,
) -> dict:
    assignee = task.assignee
    return {
        "source": source,
        "auto_claimed": auto_claimed,
        "task": {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "assignee_role": task.assignee_role,
            "assignee_id": task.assignee_id,
            "assignee_email": assignee.email if assignee else None,
            "github_repo": task.github_repo or "",
            "github_branch": task.github_branch or "",
            "expected_next_step": task.expected_next_step or "",
            "implementation_summary": task.implementation_summary or "",
            "version": task.version,
        },
        "workspace_id": task.workspace_id,
        "prompt_hint": (
            f"Fast Plan task #{task.id} ({task.title}): claim if needed, execute, "
            f"journal result, handoff when done."
        ),
    }


def emit_delivery_agent_event(
    task: DeliveryTask,
    event: str,
    *,
    auto_claimed: bool = False,
    source: str = "assign",
) -> None:
    try:
        from workspaces.webhooks import emit_webhook

        emit_webhook(
            task.workspace,
            event,
            _task_webhook_payload(task, auto_claimed=auto_claimed, source=source),
            dedupe_key=f"{event}:{task.id}:{task.version}",
        )
    except ValueError:
        logger.debug("Webhook event %s not registered", event)
    except Exception:
        logger.exception("Failed to emit delivery webhook %s task=%s", event, task.id)


def try_auto_claim_for_assignee(task: DeliveryTask) -> tuple[DeliveryTask, bool]:
    """Claim task as assignee when service account has auto_claim_on_assign."""
    if not task.assignee_id:
        return task, False
    profile = AgentProfile.objects.filter(
        workspace=task.workspace,
        user_id=task.assignee_id,
        is_active=True,
        is_service_account=True,
        auto_claim_on_assign=True,
    ).first()
    if profile is None:
        return task, False
    if task.status == DeliveryTask.Status.IN_PROGRESS and task.assignee_id == profile.user_id:
        return task, False
    from delivery.services import claim_task

    try:
        claimed = claim_task(task, user=profile.user)
        return claimed, True
    except ValueError as exc:
        logger.warning(
            "auto-claim skipped task=%s assignee=%s: %s",
            task.id,
            profile.user_id,
            exc,
        )
        return task, False


def after_task_assigned(
    task: DeliveryTask,
    *,
    source: str = "assign",
) -> DeliveryTask:
    """Auto-claim (if configured) and notify agent runners."""
    task, auto_claimed = try_auto_claim_for_assignee(task)
    task.refresh_from_db()
    event = "delivery.task.handoff" if source == "handoff" else "delivery.task.assigned"
    emit_delivery_agent_event(task, event, auto_claimed=auto_claimed, source=source)
    return task
