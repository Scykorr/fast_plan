"""Optional AI drafting helpers for risks and project charter."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import date, timedelta

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


def _ollama_enabled() -> bool:
    return bool(os.environ.get("OLLAMA_BASE_URL", "").strip())


def _call_ollama(system: str, user: str) -> dict | None:
    if not _ollama_enabled():
        return None
    base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "format": "json",
        "stream": False,
    }
    request = urllib.request.Request(
        f"{base}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode())
        content = body["message"]["content"]
        return json.loads(content)
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, TypeError):
        logger.exception("Ollama draft request failed")
        return None


def _call_ai_json(system: str, user: str) -> tuple[dict | None, str | None]:
    if os.environ.get("OPENAI_API_KEY", "").strip():
        result = _call_openai(system, user)
        if result is not None:
            return result, "openai"
    if _ollama_enabled():
        result = _call_ollama(system, user)
        if result is not None:
            return result, "ollama"
    return None, None


def _heuristic_wbs(project) -> dict:
    root = project.wbs_nodes.filter(parent__isnull=True).order_by("id").first()
    root_code = root.code if root else "1"
    today = date.today()
    phase1 = f"{root_code}.1"
    phase2 = f"{root_code}.2"
    phase3 = f"{root_code}.3"
    return {
        "nodes": [
            {
                "code": phase1,
                "title": "Инициация и планирование",
                "node_type": "deliverable",
                "parent_code": root_code,
                "duration_days": 7,
                "start_date": today.isoformat(),
            },
            {
                "code": f"{phase1}.1",
                "title": "Kick-off и устав проекта",
                "node_type": "work_package",
                "parent_code": phase1,
                "duration_days": 3,
            },
            {
                "code": phase2,
                "title": "Реализация",
                "node_type": "deliverable",
                "parent_code": root_code,
                "duration_days": 14,
                "start_date": (today + timedelta(days=7)).isoformat(),
            },
            {
                "code": f"{phase2}.1",
                "title": f"Разработка «{project.name}»",
                "node_type": "work_package",
                "parent_code": phase2,
                "duration_days": 10,
            },
            {
                "code": phase3,
                "title": "Завершение",
                "node_type": "deliverable",
                "parent_code": root_code,
                "duration_days": 5,
                "start_date": (today + timedelta(days=21)).isoformat(),
            },
            {
                "code": f"{phase3}.1",
                "title": "Приёмка и закрытие",
                "node_type": "milestone",
                "parent_code": phase3,
                "duration_days": 1,
            },
        ],
        "dependencies": [
            {
                "predecessor_code": phase1,
                "successor_code": phase2,
                "dependency_type": "FS",
                "lag_days": 0,
            },
            {
                "predecessor_code": phase2,
                "successor_code": phase3,
                "dependency_type": "FS",
                "lag_days": 0,
            },
        ],
    }


def _next_wbs_code(nodes: list[dict], parent_code: str) -> str:
    max_suffix = 0
    prefix = f"{parent_code}."
    for node in nodes:
        code = str(node.get("code", ""))
        if not code.startswith(prefix):
            continue
        suffix_part = code[len(prefix) :].split(".", 1)[0]
        try:
            max_suffix = max(max_suffix, int(suffix_part))
        except ValueError:
            continue
    return f"{parent_code}.{max_suffix + 1}"


def _default_parent_code(nodes: list[dict], root_code: str) -> str:
    for node in nodes:
        title = str(node.get("title", "")).lower()
        if "реализац" in title:
            return str(node["code"])
    for node in nodes:
        if node.get("node_type") == "deliverable" and str(node.get("code", "")).startswith(
            f"{root_code}."
        ):
            return str(node["code"])
    return f"{root_code}.2"


def _heuristic_refine_wbs(
    project,
    nodes: list[dict],
    dependencies: list[dict],
    refinement: str,
) -> dict:
    root = project.wbs_nodes.filter(parent__isnull=True).order_by("id").first()
    root_code = root.code if root else "1"
    updated_nodes = [dict(node) for node in nodes]
    updated_deps = [dict(dep) for dep in dependencies]
    text = refinement.strip()
    text_lower = text.lower()

    if any(keyword in text_lower for keyword in ("удал", "убери", "remove", "delete")):
        codes_to_remove = {
            str(node.get("code", ""))
            for node in updated_nodes
            if str(node.get("code", "")) and str(node.get("code", "")) in text
        }
        if codes_to_remove:
            updated_nodes = [
                node for node in updated_nodes if str(node.get("code", "")) not in codes_to_remove
            ]
            updated_deps = [
                dep
                for dep in updated_deps
                if str(dep.get("predecessor_code", "")) not in codes_to_remove
                and str(dep.get("successor_code", "")) not in codes_to_remove
            ]
            return {"nodes": updated_nodes, "dependencies": updated_deps}

    parent_code = _default_parent_code(updated_nodes, root_code)

    if any(keyword in text_lower for keyword in ("тест", "qa", "testing")):
        test_code = _next_wbs_code(updated_nodes, parent_code)
        updated_nodes.append(
            {
                "code": test_code,
                "title": "Тестирование и QA",
                "node_type": "work_package",
                "parent_code": parent_code,
                "duration_days": 5,
            }
        )
    elif any(keyword in text_lower for keyword in ("деплой", "deploy", "релиз", "release")):
        deploy_parent = _next_wbs_code(updated_nodes, root_code)
        if not any(str(node.get("code", "")) == deploy_parent for node in updated_nodes):
            updated_nodes.append(
                {
                    "code": deploy_parent,
                    "title": "Деплой и релиз",
                    "node_type": "deliverable",
                    "parent_code": root_code,
                    "duration_days": 3,
                }
            )
        updated_nodes.append(
            {
                "code": _next_wbs_code(updated_nodes, deploy_parent),
                "title": "Вывод в production",
                "node_type": "milestone",
                "parent_code": deploy_parent,
                "duration_days": 1,
            }
        )
    elif text:
        updated_nodes.append(
            {
                "code": _next_wbs_code(updated_nodes, parent_code),
                "title": text[:120],
                "node_type": "work_package",
                "parent_code": parent_code,
                "duration_days": 5,
            }
        )

    return {"nodes": updated_nodes, "dependencies": updated_deps}


def refine_wbs_draft(
    project,
    *,
    nodes: list[dict],
    dependencies: list[dict],
    refinement: str,
    prompt: str = "",
) -> dict:
    if not refinement.strip():
        raise ValueError("refinement text is required.")
    if not nodes:
        raise ValueError("current draft nodes are required for refinement.")

    context = (
        f"Project: {project.name}\n"
        f"Status: {project.status}\n"
        f"Budget: {project.budget}\n"
        f"Description: {project.description or ''}\n"
        f"Base prompt: {prompt}\n"
        f"Refinement request: {refinement}"
    )
    draft_json = json.dumps(
        {"nodes": nodes, "dependencies": dependencies},
        ensure_ascii=False,
    )
    ai, ai_source = _call_ai_json(
        "You refine an existing project WBS draft. Return JSON with keys "
        '"nodes" (array of {code,title,node_type,parent_code,duration_days,start_date,end_date}) '
        'and "dependencies" (array of {predecessor_code,successor_code,dependency_type,lag_days}). '
        "Apply the refinement request to the current draft. Return the FULL updated draft. Russian titles.",
        f"{context}\n\nCurrent draft:\n{draft_json}",
    )
    if isinstance(ai, dict) and isinstance(ai.get("nodes"), list) and ai["nodes"]:
        return {
            "target": "wbs",
            "source": ai_source or "heuristic",
            "nodes": ai.get("nodes") or [],
            "dependencies": ai.get("dependencies") or [],
            "refinement": refinement,
        }
    heuristic = _heuristic_refine_wbs(project, nodes, dependencies, refinement)
    return {
        "target": "wbs",
        "source": "heuristic",
        "nodes": heuristic["nodes"],
        "dependencies": heuristic["dependencies"],
        "refinement": refinement,
    }


def draft_project_content(project, *, target: str, prompt: str = "") -> dict:
    context = (
        f"Project: {project.name}\n"
        f"Status: {project.status}\n"
        f"Budget: {project.budget}\n"
        f"Description: {project.description or ''}\n"
        f"Extra prompt: {prompt}"
    )
    if target == "risks":
        ai, ai_source = _call_ai_json(
            "You are a project risk analyst. Return JSON {\"risks\":[{"
            "\"title\",\"description\",\"probability\",\"impact\",\"mitigation\",\"status\"}]}. "
            "probability/impact are 1-5 integers. status is open.",
            context,
        )
        risks = (ai or {}).get("risks") if isinstance(ai, dict) else None
        return {
            "target": "risks",
            "source": ai_source or "heuristic",
            "risks": risks or _heuristic_risks(project),
        }

    if target == "charter":
        ai, ai_source = _call_ai_json(
            "You are a PMO assistant. Return JSON with keys "
            "goals, success_criteria, constraints, assumptions as Russian strings.",
            context,
        )
        if isinstance(ai, dict) and {"goals", "success_criteria", "constraints", "assumptions"} <= set(
            ai
        ):
            return {"target": "charter", "source": ai_source or "heuristic", "charter": ai}
        return {
            "target": "charter",
            "source": "heuristic",
            "charter": _heuristic_charter(project),
        }

    if target == "wbs":
        ai, ai_source = _call_ai_json(
            "You are a project planner. Return JSON with keys "
            '"nodes" (array of {code,title,node_type,parent_code,duration_days,start_date,end_date}) '
            'and "dependencies" (array of {predecessor_code,successor_code,dependency_type,lag_days}). '
            "Use hierarchical codes like 1.1, 1.2 under project root. node_type: deliverable, work_package, milestone. "
            "dependency_type: FS, SS, FF, SF. Russian titles.",
            context,
        )
        if isinstance(ai, dict) and isinstance(ai.get("nodes"), list):
            return {
                "target": "wbs",
                "source": ai_source or "heuristic",
                "nodes": ai.get("nodes") or [],
                "dependencies": ai.get("dependencies") or [],
            }
        heuristic = _heuristic_wbs(project)
        return {
            "target": "wbs",
            "source": "heuristic",
            "nodes": heuristic["nodes"],
            "dependencies": heuristic["dependencies"],
        }

    raise ValueError("target must be 'risks', 'charter', or 'wbs'")
