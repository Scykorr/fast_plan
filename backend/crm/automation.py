"""BPM-lite automation engine: trigger → conditions → actions."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from crm.models import (
    Activity,
    AutomationDeferred,
    AutomationRule,
    AutomationRun,
    Deal,
    DealTask,
    Lead,
)
from crm.services import (
    assign_lead_round_robin,
    convert_lead_to_deal,
)


AUTOMATION_TEMPLATES = {
    "form_lead": {
        "name": "Лид из формы → assign + заметка",
        "trigger": AutomationRule.Trigger.LEAD_CREATED,
        "conditions": [
            {"field": "source", "op": "in", "value": ["form", "website"]},
        ],
        "actions": [
            {"type": "assign_round_robin"},
            {
                "type": "create_activity",
                "kind": "note",
                "subject": "Лид из формы — первичный контакт",
                "body": "Автоматически создано правилом «Лид из формы».",
            },
        ],
    },
    "follow_up_2d": {
        "name": "Сделка создана → follow-up +2 дня",
        "trigger": AutomationRule.Trigger.DEAL_CREATED,
        "conditions": [],
        "actions": [
            {
                "type": "create_deal_task",
                "title": "Follow-up по сделке",
                "due_in_days": 2,
                "remind_before_days": 1,
            },
        ],
    },
    "stale_deal_daily": {
        "name": "Ежедневно: stale deals → задача",
        "trigger": AutomationRule.Trigger.SCHEDULE_DAILY,
        "conditions": [
            {"field": "days_since_touch", "op": "gte", "value": 14},
        ],
        "actions": [
            {
                "type": "create_deal_task",
                "title": "Stale deal — вернуть в контакт",
                "due_in_days": 1,
                "remind_before_days": 0,
                "notes": "Автоматизация schedule.daily",
                "skip_if_open": True,
            },
        ],
    },
}


def _get_field(context: dict, field: str):
    if field in context:
        return context.get(field)
    entity = context.get("lead") or context.get("deal") or {}
    if isinstance(entity, dict):
        return entity.get(field)
    return getattr(entity, field, None)


def _match_condition(condition: dict, context: dict) -> bool:
    field = condition.get("field") or ""
    op = (condition.get("op") or "eq").lower()
    expected = condition.get("value")
    actual = _get_field(context, field)
    if op == "eq":
        return str(actual).lower() == str(expected).lower() if actual is not None else expected in (None, "")
    if op == "neq":
        return str(actual).lower() != str(expected).lower()
    if op == "contains":
        return str(expected).lower() in str(actual or "").lower()
    if op == "in":
        values = expected if isinstance(expected, (list, tuple)) else [expected]
        return str(actual).lower() in {str(v).lower() for v in values}
    if op in ("gte", "lte"):
        try:
            a = float(actual)
            b = float(expected)
        except (TypeError, ValueError):
            return False
        return a >= b if op == "gte" else a <= b
    return False


def conditions_match(conditions: list, context: dict) -> bool:
    if not conditions:
        return True
    return all(_match_condition(cond, context) for cond in conditions)


def _lead_from_context(context: dict) -> Lead | None:
    lead = context.get("lead_obj")
    if isinstance(lead, Lead):
        return lead
    lead_id = context.get("lead_id") or (context.get("lead") or {}).get("id")
    if lead_id:
        return Lead.objects.filter(pk=lead_id).first()
    return None


def _deal_from_context(context: dict) -> Deal | None:
    deal = context.get("deal_obj")
    if isinstance(deal, Deal):
        return deal
    deal_id = context.get("deal_id") or (context.get("deal") or {}).get("id")
    if deal_id:
        return Deal.objects.filter(pk=deal_id).first()
    return None


def execute_actions(workspace, actions: list, context: dict, *, rule=None) -> list[dict]:
    results = []
    remaining = list(actions or [])
    while remaining:
        action = remaining.pop(0)
        action_type = (action.get("type") or "").strip()
        try:
            if action_type == "delay":
                minutes = int(action.get("minutes") or action.get("delay_minutes") or 0)
                days = int(action.get("days") or 0)
                run_at = timezone.now() + timedelta(minutes=minutes, days=days)
                AutomationDeferred.objects.create(
                    workspace=workspace,
                    rule=rule,
                    actions=remaining,
                    context=_serialize_context(context),
                    run_at=run_at,
                )
                results.append({"type": "delay", "run_at": run_at.isoformat(), "ok": True})
                remaining = []
                break

            if action_type == "assign_round_robin":
                lead = _lead_from_context(context)
                user = assign_lead_round_robin(workspace)
                if lead and user:
                    lead.assigned_to = user
                    lead.save(update_fields=["assigned_to", "updated_at"])
                results.append(
                    {
                        "type": action_type,
                        "ok": bool(user),
                        "user_id": user.id if user else None,
                    }
                )
                continue

            if action_type == "assign":
                lead = _lead_from_context(context)
                deal = _deal_from_context(context)
                user_id = action.get("user_id")
                from workspaces.models import WorkspaceMember

                member = WorkspaceMember.objects.filter(
                    workspace=workspace, user_id=user_id
                ).select_related("user").first()
                if member and lead:
                    lead.assigned_to = member.user
                    lead.save(update_fields=["assigned_to", "updated_at"])
                if member and deal:
                    deal.owner = member.user
                    deal.save(update_fields=["owner", "updated_at"])
                results.append(
                    {"type": action_type, "ok": bool(member), "user_id": user_id}
                )
                continue

            if action_type == "create_deal_task":
                deal = _deal_from_context(context)
                if deal is None:
                    results.append({"type": action_type, "ok": False, "error": "no deal"})
                    continue
                title = action.get("title") or "Автозадача"
                if action.get("skip_if_open"):
                    exists = DealTask.objects.filter(
                        deal=deal, is_done=False, title=title
                    ).exists()
                    if exists:
                        results.append(
                            {
                                "type": action_type,
                                "ok": True,
                                "skipped": True,
                                "reason": "open task exists",
                            }
                        )
                        continue
                due_in = int(action.get("due_in_days") or 0)
                due_date = (timezone.localdate() + timedelta(days=due_in)) if due_in else None
                task = DealTask.objects.create(
                    deal=deal,
                    title=title,
                    due_date=due_date,
                    remind_before_days=int(action.get("remind_before_days") or 1),
                    assignee=deal.owner,
                    notes=action.get("notes") or "",
                )
                results.append({"type": action_type, "ok": True, "task_id": task.id})
                continue

            if action_type == "create_activity":
                lead = _lead_from_context(context)
                deal = _deal_from_context(context)
                person = lead.person if lead else (deal.person if deal else None)
                organization = (
                    lead.organization if lead else (deal.organization if deal else None)
                )
                if person is None and organization is None and lead is None:
                    results.append({"type": action_type, "ok": False, "error": "no target"})
                    continue
                # Activity requires person or organization; bind via person from lead if needed
                if person is None and lead is not None and lead.email:
                    from crm.models import Person

                    person = Person.objects.filter(
                        workspace=workspace, email__iexact=lead.email
                    ).first()
                if person is None and organization is None:
                    # Create a note-like activity on organization after ensuring org
                    from crm.models import Organization

                    if lead and lead.company_name:
                        organization, _ = Organization.objects.get_or_create(
                            workspace=workspace,
                            name=lead.company_name,
                        )
                if person is None and organization is None:
                    results.append({"type": action_type, "ok": False, "error": "no target"})
                    continue
                activity = Activity.objects.create(
                    workspace=workspace,
                    kind=action.get("kind") or Activity.Kind.NOTE,
                    subject=action.get("subject") or "Автоматизация",
                    body=action.get("body") or "",
                    occurred_at=timezone.now(),
                    person=person,
                    organization=organization,
                    project=deal.project if deal else None,
                )
                results.append({"type": action_type, "ok": True, "activity_id": activity.id})
                continue

            if action_type == "create_deal":
                lead = _lead_from_context(context)
                if lead is None:
                    results.append({"type": action_type, "ok": False, "error": "no lead"})
                    continue
                if lead.status == Lead.Status.CONVERTED and lead.deal_id:
                    results.append(
                        {"type": action_type, "ok": True, "deal_id": lead.deal_id, "skipped": True}
                    )
                    continue
                amount = action.get("amount")
                amount_dec = None
                if amount not in (None, ""):
                    try:
                        amount_dec = Decimal(str(amount))
                    except (InvalidOperation, TypeError, ValueError):
                        amount_dec = None
                deal = convert_lead_to_deal(
                    lead, title=action.get("title"), amount=amount_dec
                )
                context["deal_obj"] = deal
                context["deal_id"] = deal.id
                # Nested deal.created automations (skip recursive create_deal loops via converted skip)
                run_automations(
                    workspace,
                    AutomationRule.Trigger.DEAL_CREATED,
                    build_deal_context(
                        deal, trigger=AutomationRule.Trigger.DEAL_CREATED
                    ),
                )
                results.append({"type": action_type, "ok": True, "deal_id": deal.id})
                continue

            if action_type == "create_lead":
                lead = Lead.objects.create(
                    workspace=workspace,
                    full_name=action.get("full_name") or "Automation lead",
                    email=action.get("email") or "",
                    phone=action.get("phone") or "",
                    company_name=action.get("company_name") or "",
                    source=action.get("source") or "automation",
                    notes=action.get("notes") or "",
                    score=int(action.get("score") or 0),
                )
                context["lead_obj"] = lead
                context["lead_id"] = lead.id
                results.append({"type": action_type, "ok": True, "lead_id": lead.id})
                continue

            if action_type == "set_status":
                lead = _lead_from_context(context)
                status_value = action.get("status")
                if lead and status_value in Lead.Status.values:
                    lead.status = status_value
                    lead.save(update_fields=["status", "updated_at"])
                    results.append({"type": action_type, "ok": True, "status": status_value})
                else:
                    results.append({"type": action_type, "ok": False})
                continue

            if action_type == "webhook":
                from workspaces.webhooks import emit_webhook

                event = action.get("event") or "crm.automation"
                payload = {
                    "rule_id": rule.id if rule else None,
                    "trigger": context.get("trigger"),
                    "lead_id": context.get("lead_id"),
                    "deal_id": context.get("deal_id"),
                    "extra": action.get("payload") or {},
                }
                try:
                    count = emit_webhook(
                        workspace,
                        event,
                        payload,
                        dedupe_key=action.get("dedupe_key"),
                    )
                    results.append({"type": action_type, "ok": True, "deliveries": count})
                except ValueError as exc:
                    results.append({"type": action_type, "ok": False, "error": str(exc)})
                continue

            results.append({"type": action_type or "unknown", "ok": False, "error": "unknown action"})
        except Exception as exc:  # noqa: BLE001 — per-action isolation
            results.append({"type": action_type, "ok": False, "error": str(exc)})
    return results


def _serialize_context(context: dict) -> dict:
    out = {
        "trigger": context.get("trigger"),
        "lead_id": context.get("lead_id"),
        "deal_id": context.get("deal_id"),
        "source": context.get("source"),
        "status": context.get("status"),
        "stage_id": context.get("stage_id"),
        "from_stage_id": context.get("from_stage_id"),
        "days_since_touch": context.get("days_since_touch"),
    }
    lead = context.get("lead")
    if isinstance(lead, dict):
        out["lead"] = lead
    deal = context.get("deal")
    if isinstance(deal, dict):
        out["deal"] = deal
    return {k: v for k, v in out.items() if v is not None}


def build_lead_context(lead: Lead, *, trigger: str) -> dict:
    return {
        "trigger": trigger,
        "lead_obj": lead,
        "lead_id": lead.id,
        "source": lead.source,
        "status": lead.status,
        "score": lead.score,
        "lead": {
            "id": lead.id,
            "full_name": lead.full_name,
            "email": lead.email,
            "phone": lead.phone,
            "company_name": lead.company_name,
            "source": lead.source,
            "status": lead.status,
            "score": lead.score,
        },
    }


def build_deal_context(deal: Deal, *, trigger: str, from_stage_id=None) -> dict:
    from crm.ai import deal_days_since_touch

    touch_days = deal_days_since_touch(deal)
    return {
        "trigger": trigger,
        "deal_obj": deal,
        "deal_id": deal.id,
        "stage_id": deal.stage_id,
        "from_stage_id": from_stage_id,
        "amount": float(deal.amount),
        "probability": deal.probability,
        "days_since_touch": touch_days,
        "deal": {
            "id": deal.id,
            "title": deal.title,
            "stage_id": deal.stage_id,
            "amount": float(deal.amount),
            "probability": deal.probability,
            "organization_id": deal.organization_id,
            "days_since_touch": touch_days,
        },
    }


def run_schedule_daily_automations(*, workspace=None) -> dict:
    """Run schedule.daily rules for open deals (e.g. stale follow-ups)."""
    from workspaces.models import Workspace

    workspaces = [workspace] if workspace is not None else list(Workspace.objects.all())
    stats = {"workspaces": 0, "rules": 0, "runs": 0, "deals_matched": 0}
    trigger = AutomationRule.Trigger.SCHEDULE_DAILY

    for ws in workspaces:
        rules = list(
            AutomationRule.objects.filter(workspace=ws, is_active=True, trigger=trigger)
        )
        if not rules:
            continue
        stats["workspaces"] += 1
        stats["rules"] += len(rules)
        open_deals = (
            Deal.objects.filter(workspace=ws)
            .select_related("stage", "organization", "person")
            .exclude(stage__is_won=True)
            .exclude(stage__is_lost=True)
        )
        for deal in open_deals:
            context = build_deal_context(deal, trigger=trigger)
            matched_any = False
            for rule in rules:
                if not conditions_match(rule.conditions or [], context):
                    continue
                matched_any = True
                try:
                    results = execute_actions(
                        ws, rule.actions or [], context, rule=rule
                    )
                    success = (
                        all(item.get("ok", False) for item in results) if results else True
                    )
                    AutomationRun.objects.create(
                        rule=rule,
                        workspace=ws,
                        trigger=trigger,
                        context=_serialize_context(context),
                        result={"actions": results},
                        success=success,
                    )
                    stats["runs"] += 1
                except Exception as exc:  # noqa: BLE001
                    AutomationRun.objects.create(
                        rule=rule,
                        workspace=ws,
                        trigger=trigger,
                        context=_serialize_context(context),
                        result={"error": str(exc)},
                        success=False,
                    )
                    stats["runs"] += 1
            if matched_any:
                stats["deals_matched"] += 1
    return stats


def run_automations(workspace, trigger: str, context: dict) -> list[AutomationRun]:
    rules = AutomationRule.objects.filter(
        workspace=workspace, is_active=True, trigger=trigger
    )
    runs = []
    enriched = {**context, "trigger": trigger}
    for rule in rules:
        if not conditions_match(rule.conditions or [], enriched):
            continue
        try:
            results = execute_actions(
                workspace, rule.actions or [], enriched, rule=rule
            )
            success = all(item.get("ok", False) for item in results) if results else True
            run = AutomationRun.objects.create(
                rule=rule,
                workspace=workspace,
                trigger=trigger,
                context=_serialize_context(enriched),
                result={"actions": results},
                success=success,
            )
            runs.append(run)
        except Exception as exc:  # noqa: BLE001
            run = AutomationRun.objects.create(
                rule=rule,
                workspace=workspace,
                trigger=trigger,
                context=_serialize_context(enriched),
                result={"error": str(exc)},
                success=False,
            )
            runs.append(run)
    return runs


def process_deferred_automations(*, now=None) -> int:
    now = now or timezone.now()
    qs = AutomationDeferred.objects.filter(
        processed_at__isnull=True, run_at__lte=now
    ).select_related("workspace", "rule")
    processed = 0
    for item in qs:
        context = dict(item.context or {})
        if context.get("lead_id"):
            lead = Lead.objects.filter(pk=context["lead_id"]).first()
            if lead:
                context["lead_obj"] = lead
        if context.get("deal_id"):
            deal = Deal.objects.filter(pk=context["deal_id"]).first()
            if deal:
                context["deal_obj"] = deal
        execute_actions(
            item.workspace, item.actions or [], context, rule=item.rule
        )
        item.processed_at = now
        item.save(update_fields=["processed_at"])
        processed += 1
    return processed


def apply_template(workspace, template_key: str) -> AutomationRule:
    template = AUTOMATION_TEMPLATES.get(template_key)
    if template is None:
        raise ValueError(f"Unknown template: {template_key}")
    rule, _ = AutomationRule.objects.update_or_create(
        workspace=workspace,
        template_key=template_key,
        defaults={
            "name": template["name"],
            "trigger": template["trigger"],
            "conditions": template["conditions"],
            "actions": template["actions"],
            "is_active": True,
        },
    )
    return rule


def apply_deal_move(deal: Deal, stage, *, position=None, probability=None) -> Deal:
    """Move deal to stage and reindex positions in old/new columns."""
    old_stage = deal.stage
    if probability is None:
        probability = (
            stage.default_probability
            if stage.id != old_stage.id
            else deal.probability
        )

    new_siblings = list(
        Deal.objects.filter(stage=stage)
        .exclude(pk=deal.pk)
        .order_by("position", "id")
    )
    if position is None:
        position = len(new_siblings)
    position = max(0, min(int(position), len(new_siblings)))

    deal.stage = stage
    deal.probability = probability
    new_siblings.insert(position, deal)

    for idx, item in enumerate(new_siblings):
        item.position = idx
        item.stage = stage
        if item.pk == deal.pk:
            item.probability = probability

    Deal.objects.bulk_update(
        [item for item in new_siblings if item.pk != deal.pk],
        ["position", "stage"],
    )
    deal.position = position
    deal.save(update_fields=["stage", "position", "probability", "updated_at"])

    if old_stage.id != stage.id:
        old_siblings = list(
            Deal.objects.filter(stage=old_stage).order_by("position", "id")
        )
        changed = []
        for idx, item in enumerate(old_siblings):
            if item.position != idx:
                item.position = idx
                changed.append(item)
        if changed:
            Deal.objects.bulk_update(changed, ["position"])
    return deal
