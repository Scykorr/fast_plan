"""Optional AI drafting helpers for risks and project charter."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger("fast_plan")


def _heuristic_risks(project) -> list[dict]:
    description = (project.description or "").strip() or project.name
    seeds = [
        (
            f"Срыв сроков по «{project.name}»",
            "Ключевые работы могут затянуться из‑за недооценки сложности.",
            4,
            4,
            "Зафиксировать буфер на критическом пути и еженедельный контроль SPI.",
        ),
        (
            "Перерасход бюджета",
            f"Фактические затраты могут превысить план ({project.budget}).",
            3,
            4,
            "Согласовать порог эскалации и еженедельный CPI-review.",
        ),
        (
            "Недостаточная вовлечённость стейкхолдеров",
            f"Контекст проекта: {description[:180]}",
            3,
            3,
            "Назначить регулярные статус-встречи и RACI по ключевым deliverables.",
        ),
    ]
    return [
        {
            "title": title,
            "description": desc,
            "probability": probability,
            "impact": impact,
            "mitigation": mitigation,
            "status": "open",
        }
        for title, desc, probability, impact, mitigation in seeds
    ]


def _heuristic_charter(project) -> dict:
    description = (project.description or "").strip()
    return {
        "goals": (
            f"Доставить результат проекта «{project.name}» "
            f"в рамках согласованного бюджета и сроков."
        ),
        "success_criteria": (
            "Достигнут целевой прогресс по WBS, SPI/CPI ≥ 0.9, "
            "критические риски закрыты или митигированы."
        ),
        "constraints": (
            f"Бюджет: {project.budget}. "
            f"Срок: {project.start_date or '—'} → {project.end_date or '—'}."
        ),
        "assumptions": (
            description
            or "Команда и стейкхолдеры доступны; требования стабильны на горизонте планирования."
        ),
    }


def _call_openai(system: str, user: str) -> dict | None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode())
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, TypeError):
        logger.exception("OpenAI draft request failed")
        return None


def draft_project_content(project, *, target: str, prompt: str = "") -> dict:
    context = (
        f"Project: {project.name}\n"
        f"Status: {project.status}\n"
        f"Budget: {project.budget}\n"
        f"Description: {project.description or ''}\n"
        f"Extra prompt: {prompt}"
    )
    if target == "risks":
        ai = _call_openai(
            "You are a project risk analyst. Return JSON {\"risks\":[{"
            "\"title\",\"description\",\"probability\",\"impact\",\"mitigation\",\"status\"}]}. "
            "probability/impact are 1-5 integers. status is open.",
            context,
        )
        risks = (ai or {}).get("risks") if isinstance(ai, dict) else None
        return {
            "target": "risks",
            "source": "openai" if risks else "heuristic",
            "risks": risks or _heuristic_risks(project),
        }

    if target == "charter":
        ai = _call_openai(
            "You are a PMO assistant. Return JSON with keys "
            "goals, success_criteria, constraints, assumptions as Russian strings.",
            context,
        )
        if isinstance(ai, dict) and {"goals", "success_criteria", "constraints", "assumptions"} <= set(
            ai
        ):
            return {"target": "charter", "source": "openai", "charter": ai}
        return {
            "target": "charter",
            "source": "heuristic",
            "charter": _heuristic_charter(project),
        }

    raise ValueError("target must be 'risks' or 'charter'")
