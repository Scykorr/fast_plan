"""AI CRM helpers: insights, drafts, activity summaries, suggested tasks."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from crm.models import Activity, Deal, DealTask, Organization, Person
from crm.services import annotate_last_activity, days_since_touch, filter_stale
from projects.ai import _call_ai_json


def deal_last_touch_at(deal: Deal):
    """Latest touch: deal update or linked person/org/project activity."""
    stamps = [deal.updated_at, deal.created_at]
    filters = Q()
    if deal.person_id:
        filters |= Q(person_id=deal.person_id)
    if deal.organization_id:
        filters |= Q(organization_id=deal.organization_id)
    if deal.project_id:
        filters |= Q(project_id=deal.project_id)
    if filters:
        last = (
            Activity.objects.filter(workspace_id=deal.workspace_id)
            .filter(filters)
            .order_by("-occurred_at")
            .values_list("occurred_at", flat=True)
            .first()
        )
        if last:
            stamps.append(last)
    return max(stamps)


def deal_days_since_touch(deal: Deal) -> int:
    last = deal_last_touch_at(deal)
    return max(0, (timezone.now() - last).days)


def _open_deals(workspace):
    return (
        Deal.objects.filter(workspace=workspace)
        .select_related("stage", "organization", "person", "owner")
        .exclude(stage__is_won=True)
        .exclude(stage__is_lost=True)
    )


def build_crm_insights(workspace, *, stale_days: int = 14) -> dict:
    today = timezone.localdate()
    stale_people = list(
        filter_stale(annotate_last_activity(Person.objects.filter(workspace=workspace)), stale_days)[
            :20
        ]
    )
    stale_orgs = list(
        filter_stale(
            annotate_last_activity(
                Organization.objects.filter(workspace=workspace), person=False
            ),
            stale_days,
        )[:20]
    )

    open_deals = list(_open_deals(workspace)[:200])
    at_risk = []
    for deal in open_deals:
        reasons = []
        touch_days = deal_days_since_touch(deal)
        if touch_days >= stale_days:
            reasons.append(f"нет касаний {touch_days} дн.")
        if deal.probability is not None and deal.probability < 40:
            reasons.append(f"низкая вероятность {deal.probability}%")
        if deal.close_date and deal.close_date < today:
            reasons.append("просрочен close_date")
        elif deal.close_date and deal.close_date <= today + timedelta(days=7):
            reasons.append("close_date ≤ 7 дней")
        overdue_tasks = DealTask.objects.filter(
            deal=deal, is_done=False, due_date__lt=today
        ).count()
        if overdue_tasks:
            reasons.append(f"просроченных задач: {overdue_tasks}")
        if reasons:
            at_risk.append(
                {
                    "id": deal.id,
                    "title": deal.title,
                    "amount": float(deal.amount),
                    "probability": deal.probability,
                    "close_date": deal.close_date.isoformat() if deal.close_date else None,
                    "days_since_touch": touch_days,
                    "reasons": reasons,
                    "organization_name": deal.organization.name if deal.organization else None,
                }
            )
    at_risk.sort(key=lambda row: (-len(row["reasons"]), -row["days_since_touch"]))

    forecast = sum((d.amount * d.probability) / 100 for d in open_deals)

    narrative_bits = []
    if stale_people or stale_orgs:
        narrative_bits.append(
            f"Без касаний ≥{stale_days} дн.: {len(stale_people)} контактов, "
            f"{len(stale_orgs)} компаний."
        )
    if at_risk:
        narrative_bits.append(f"Сделок под риском: {len(at_risk)}.")
    narrative_bits.append(f"Взвешенный прогноз открытых сделок: {float(forecast):.0f}.")

    system = (
        "Ты CRM-аналитик. Верни JSON {\"summary\": \"1-3 предложения на русском\"} "
        "по данным insights."
    )
    user = (
        f"stale_people={len(stale_people)}, stale_orgs={len(stale_orgs)}, "
        f"at_risk={len(at_risk)}, forecast={float(forecast):.2f}, "
        f"top_risks={[r['title'] for r in at_risk[:5]]}"
    )
    ai_payload, source = _call_ai_json(system, user)
    summary = ""
    if isinstance(ai_payload, dict):
        summary = str(ai_payload.get("summary") or "").strip()
    if not summary:
        summary = " ".join(narrative_bits)
        source = source or "heuristic"

    return {
        "summary": summary,
        "source": source or "heuristic",
        "stale_days": stale_days,
        "forecast_amount": float(forecast),
        "stale_people": [
            {
                "id": p.id,
                "full_name": p.full_name,
                "email": p.email,
                "days_since_touch": days_since_touch(getattr(p, "last_activity_at", None)),
            }
            for p in stale_people
        ],
        "stale_organizations": [
            {
                "id": o.id,
                "name": o.name,
                "days_since_touch": days_since_touch(getattr(o, "last_activity_at", None)),
            }
            for o in stale_orgs
        ],
        "at_risk_deals": at_risk[:30],
    }


def _deal_or_person_context(workspace, *, deal_id=None, person_id=None, organization_id=None):
    deal = None
    person = None
    organization = None
    if deal_id:
        deal = (
            Deal.objects.filter(workspace=workspace, pk=deal_id)
            .select_related("organization", "person", "stage")
            .first()
        )
        if deal:
            person = deal.person
            organization = deal.organization
    if person_id and person is None:
        person = Person.objects.filter(workspace=workspace, pk=person_id).first()
    if organization_id and organization is None:
        organization = Organization.objects.filter(
            workspace=workspace, pk=organization_id
        ).first()
    return deal, person, organization


def _activities_for(workspace, *, deal=None, person=None, organization=None, limit=30):
    qs = Activity.objects.filter(workspace=workspace)
    filters = Q()
    if person:
        filters |= Q(person=person)
    if organization:
        filters |= Q(organization=organization)
    if deal and deal.project_id:
        filters |= Q(project_id=deal.project_id)
    if not filters:
        return []
    return list(qs.filter(filters).order_by("-occurred_at")[:limit])


def draft_email(workspace, *, deal_id=None, person_id=None, organization_id=None, prompt="") -> dict:
    deal, person, organization = _deal_or_person_context(
        workspace,
        deal_id=deal_id,
        person_id=person_id,
        organization_id=organization_id,
    )
    name = (
        (person.full_name if person else None)
        or (organization.name if organization else None)
        or (deal.title if deal else "коллега")
    )
    deal_title = deal.title if deal else ""
    amount = float(deal.amount) if deal else None
    heuristic_subject = f"По сделке «{deal_title}»" if deal_title else f"Контакт: {name}"
    heuristic_body = (
        f"Здравствуйте, {name}!\n\n"
        f"Хотел(а) уточнить статус "
        f"{'по сделке «' + deal_title + '»' if deal_title else 'нашего взаимодействия'}"
        f"{f' (сумма {amount:.0f})' if amount else ''}. "
        f"Буду рад(а) созвониться на этой неделе.\n\n"
        f"{(prompt or '').strip()}\n\nС уважением"
    ).strip()

    system = (
        "Ты sales-ассистент. Верни JSON "
        "{\"subject\": \"...\", \"body\": \"письмо на русском\"}."
    )
    user = (
        f"to={name}, deal={deal_title}, amount={amount}, "
        f"prompt={prompt or 'follow-up'}"
    )
    ai_payload, source = _call_ai_json(system, user)
    subject = heuristic_subject
    body = heuristic_body
    if isinstance(ai_payload, dict):
        subject = str(ai_payload.get("subject") or subject).strip() or subject
        body = str(ai_payload.get("body") or body).strip() or body
        source = source or "openai"
    else:
        source = "heuristic"
    return {"subject": subject, "body": body, "source": source}


def draft_kp(workspace, *, deal_id=None, person_id=None, organization_id=None, prompt="") -> dict:
    deal, person, organization = _deal_or_person_context(
        workspace,
        deal_id=deal_id,
        person_id=person_id,
        organization_id=organization_id,
    )
    client = (
        (organization.name if organization else None)
        or (person.full_name if person else None)
        or "Клиент"
    )
    title = deal.title if deal else "Коммерческое предложение"
    amount = float(deal.amount) if deal else 0
    heuristic = (
        f"# Коммерческое предложение\n\n"
        f"**Клиент:** {client}\n"
        f"**Предмет:** {title}\n"
        f"**Ориентир по сумме:** {amount:.0f}\n\n"
        f"## Решение\n"
        f"Предлагаем реализовать «{title}» с фокусом на срок, качество и прозрачную отчётность.\n\n"
        f"## Состав работ\n"
        f"1. Discovery и согласование scope\n"
        f"2. Реализация и контроль вех\n"
        f"3. Приёмка и сопровождение\n\n"
        f"## Следующий шаг\n"
        f"Созвон для уточнения требований"
        f"{f' — {prompt.strip()}' if prompt and prompt.strip() else '.'}\n"
    )

    system = (
        "Ты готовишь КП. Верни JSON "
        "{\"title\": \"...\", \"markdown\": \"текст КП markdown на русском\"}."
    )
    user = f"client={client}, title={title}, amount={amount}, prompt={prompt or ''}"
    ai_payload, source = _call_ai_json(system, user)
    out_title = title
    markdown = heuristic
    if isinstance(ai_payload, dict):
        out_title = str(ai_payload.get("title") or out_title).strip() or out_title
        markdown = str(ai_payload.get("markdown") or markdown).strip() or markdown
        source = source or "openai"
    else:
        source = "heuristic"
    return {"title": out_title, "markdown": markdown, "source": source}


def summarize_activity(
    workspace, *, deal_id=None, person_id=None, organization_id=None, prompt=""
) -> dict:
    deal, person, organization = _deal_or_person_context(
        workspace,
        deal_id=deal_id,
        person_id=person_id,
        organization_id=organization_id,
    )
    activities = _activities_for(
        workspace, deal=deal, person=person, organization=organization
    )
    lines = [
        f"- [{a.occurred_at.date().isoformat()}] {a.kind}: {a.subject}"
        + (f" — {a.body[:120]}" if a.body else "")
        for a in activities
    ]
    if not lines:
        summary = "Активностей пока нет — стоит запланировать первый контакт."
        return {"summary": summary, "highlights": [], "source": "heuristic", "count": 0}

    heuristic_summary = (
        f"Найдено {len(activities)} активностей. "
        f"Последняя: {activities[0].kind} «{activities[0].subject}» "
        f"({activities[0].occurred_at.date().isoformat()})."
    )
    highlights = [a.subject for a in activities[:5]]

    system = (
        "Ты CRM-ассистент. Верни JSON "
        "{\"summary\": \"2-4 предложения\", \"highlights\": [\"...\"]} на русском."
    )
    user = f"prompt={prompt or ''}\nactivities:\n" + "\n".join(lines[:20])
    ai_payload, source = _call_ai_json(system, user)
    summary = heuristic_summary
    if isinstance(ai_payload, dict):
        summary = str(ai_payload.get("summary") or summary).strip() or summary
        hl = ai_payload.get("highlights")
        if isinstance(hl, list) and hl:
            highlights = [str(x) for x in hl[:8]]
        source = source or "openai"
    else:
        source = "heuristic"
    return {
        "summary": summary,
        "highlights": highlights,
        "source": source,
        "count": len(activities),
    }


def suggest_deal_tasks(workspace, *, deal_id: int, apply: bool = False) -> dict:
    deal = (
        Deal.objects.filter(workspace=workspace, pk=deal_id)
        .select_related("stage", "organization", "person")
        .first()
    )
    if deal is None:
        return {"tasks": [], "created": [], "source": "heuristic", "error": "deal not found"}

    touch_days = deal_days_since_touch(deal)
    suggestions = [
        {
            "title": "Follow-up по сделке",
            "due_in_days": 2,
            "notes": "Напомнить о статусе и следующем шаге",
        }
    ]
    if touch_days >= 7:
        suggestions.append(
            {
                "title": "Вернуть в контакт (stale)",
                "due_in_days": 1,
                "notes": f"Нет касаний {touch_days} дн.",
            }
        )
    if deal.close_date and deal.close_date <= timezone.localdate() + timedelta(days=14):
        suggestions.append(
            {
                "title": "Подготовить закрытие / КП",
                "due_in_days": 3,
                "notes": "Близкий close_date",
            }
        )
    if deal.probability < 50:
        suggestions.append(
            {
                "title": "Квалификация риска сделки",
                "due_in_days": 3,
                "notes": f"Вероятность {deal.probability}%",
            }
        )

    system = (
        "Ты CRM-ассистент. Верни JSON {\"tasks\": [{\"title\": \"...\", "
        "\"due_in_days\": 1, \"notes\": \"...\"}]} — до 5 задач на русском."
    )
    user = (
        f"deal={deal.title}, amount={deal.amount}, probability={deal.probability}, "
        f"days_since_touch={touch_days}, close_date={deal.close_date}"
    )
    ai_payload, source = _call_ai_json(system, user)
    if isinstance(ai_payload, dict) and isinstance(ai_payload.get("tasks"), list):
        parsed = []
        for item in ai_payload["tasks"][:5]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            parsed.append(
                {
                    "title": title,
                    "due_in_days": int(item.get("due_in_days") or 2),
                    "notes": str(item.get("notes") or ""),
                }
            )
        if parsed:
            suggestions = parsed
            source = source or "openai"
        else:
            source = "heuristic"
    else:
        source = "heuristic"

    created = []
    if apply:
        today = timezone.localdate()
        for item in suggestions:
            due = today + timedelta(days=int(item.get("due_in_days") or 0))
            task = DealTask.objects.create(
                deal=deal,
                title=item["title"],
                due_date=due,
                remind_before_days=1,
                assignee=deal.owner,
                notes=item.get("notes") or "",
            )
            created.append({"id": task.id, "title": task.title, "due_date": due.isoformat()})

    return {"tasks": suggestions, "created": created, "source": source}
