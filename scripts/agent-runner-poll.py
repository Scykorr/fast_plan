#!/usr/bin/env python3
"""
Poll Fast Plan Agent Ops inbox and notify external runners (Cursor / Codex).

Usage (single agent):
  set FAST_PLAN_BASE_URL=http://127.0.0.1:8080
  set FAST_PLAN_TOKEN=fp_...
  set FAST_PLAN_WORKSPACE_ID=1
  python scripts/agent-runner-poll.py

Optional:
  AGENT_RUNNER_INTERVAL_SEC=60
  AGENT_RUNNER_CALLBACK_URL=https://your-runner/trigger
  AGENT_RUNNER_STATE=.agent-runner-state.json
  AGENT_RUNNER_ONCE=1   # single poll, exit (for cron)

Multi-agent config file (JSON array):
  AGENT_RUNNER_CONFIG=scripts/agent-runner.config.example.json
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

WORK_BUCKETS = (
    "in_progress",
    "new_assignments",
    "returned_for_rework",
    "waiting_response",
)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _resolve_config_path(raw: str) -> Path:
    """Resolve config path on Windows host and Linux Docker (normalize slashes)."""
    if not raw:
        return Path()
    normalized = raw.replace("\\", "/")
    path = Path(normalized)
    if path.is_file():
        return path
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir / path.name,
        script_dir / path,
        Path.cwd() / path,
        Path("/app/scripts") / path.name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return path


def _apply_base_url_override(agents: list[dict]) -> list[dict]:
    """Docker: set AGENT_RUNNER_BASE_URL=http://frontend so host 127.0.0.1 configs work."""
    override = _env("AGENT_RUNNER_BASE_URL").rstrip("/")
    if not override:
        return agents
    for agent in agents:
        agent["base_url"] = override
    return agents


def _load_agents() -> list[dict]:
    config_path = _resolve_config_path(_env("AGENT_RUNNER_CONFIG"))
    if config_path and str(config_path):
        if not config_path.is_file():
            raise SystemExit(
                f"AGENT_RUNNER_CONFIG not found: {config_path} "
                f"(cwd={Path.cwd()}, script_dir={Path(__file__).resolve().parent})"
            )
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise SystemExit("AGENT_RUNNER_CONFIG must be a JSON array")
        return _apply_base_url_override(data)
    base = _env("FAST_PLAN_BASE_URL")
    token = _env("FAST_PLAN_TOKEN")
    ws = _env("FAST_PLAN_WORKSPACE_ID")
    if not base or not token or not ws:
        raise SystemExit(
            "Set FAST_PLAN_BASE_URL, FAST_PLAN_TOKEN, FAST_PLAN_WORKSPACE_ID "
            "or AGENT_RUNNER_CONFIG"
        )
    return _apply_base_url_override(
        [
            {
                "name": _env("AGENT_RUNNER_NAME", "agent"),
                "base_url": base.rstrip("/"),
                "token": token,
                "workspace_id": int(ws),
            }
        ]
    )


def _state_path() -> Path:
    return Path(_env("AGENT_RUNNER_STATE", ".agent-runner-state.json"))


def _load_state() -> dict:
    path = _state_path()
    if not path.exists():
        return {"seen": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    _state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")


def _api_get(agent: dict, path: str) -> dict:
    url = f"{agent['base_url']}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {agent['token']}",
            "X-Workspace-Id": str(agent["workspace_id"]),
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _callback(payload: dict) -> None:
    url = _env("AGENT_RUNNER_CALLBACK_URL")
    if not url:
        return
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30):
        pass


WORK_BUCKETS = (
    "in_progress",
    "new_assignments",
    "returned_for_rework",
    "waiting_response",
)


def _prompt_for_delivery(task: dict, agent_name: str) -> str:
    tid = task.get("id")
    title = task.get("title", "")
    status = task.get("status", "")
    branch = task.get("github_branch") or ""
    next_step = task.get("expected_next_step") or ""
    parts = [
        f"[{agent_name}] Agent Ops #{tid}: {title}",
        f"Status: {status}.",
    ]
    if branch:
        parts.append(f"Branch: {branch}.")
    if next_step:
        parts.append(f"Expected: {next_step}.")
    parts.append(
        "Execute: read journal, implement, commit to agent branch, "
        "POST result comment, handoff when done."
    )
    return " ".join(parts)


def _prompt_for_wbs(task: dict, agent_name: str) -> str:
    wid = task.get("wbs_id")
    title = task.get("title", "")
    project = task.get("project_name", "")
    desc = (task.get("description") or "").strip()
    parts = [
        f"[{agent_name}] WBS #{wid}: {title}",
        f"Project: {project}.",
    ]
    if desc:
        parts.append(f"Description: {desc[:300]}.")
    parts.append(
        "Execute: implement in project repo, PATCH wbs description with summary, "
        "POST wbs comment, set progress=100 if schedule_activity_id present."
    )
    return " ".join(parts)


def _task_key(agent_name: str, source: str, task_id: int, version: int = 0) -> str:
    return f"{agent_name}:{source}:{task_id}:v{version}"


def _emit_trigger(
    *,
    triggers: list[dict],
    seen: dict,
    agent_name: str,
    source: str,
    bucket: str,
    task_id: int,
    task: dict,
    prompt: str,
    version: int = 0,
) -> None:
    key = _task_key(agent_name, source, task_id, version)
    if key in seen:
        return
    seen[key] = {"bucket": bucket, "source": source, "at": time.time()}
    trigger = {
        "agent": agent_name,
        "source": source,
        "bucket": bucket,
        "task_id": task_id,
        "task": task,
        "prompt": prompt,
    }
    triggers.append(trigger)
    print(trigger["prompt"])
    try:
        _callback(trigger)
    except Exception as exc:  # noqa: BLE001
        print(f"[{agent_name}] callback failed: {exc}", file=sys.stderr)


def poll_once(state: dict) -> list[dict]:
    triggers: list[dict] = []
    seen: dict = state.setdefault("seen", {})

    for agent in _load_agents():
        name = agent.get("name") or "agent"
        try:
            inbox = _api_get(agent, "/api/delivery/my-tasks/")
        except urllib.error.HTTPError as exc:
            print(f"[{name}] inbox HTTP {exc.code}", file=sys.stderr)
            continue
        except urllib.error.URLError as exc:
            print(f"[{name}] inbox error: {exc.reason}", file=sys.stderr)
            continue

        for bucket in WORK_BUCKETS:
            for task in inbox.get(bucket) or []:
                _emit_trigger(
                    triggers=triggers,
                    seen=seen,
                    agent_name=name,
                    source="delivery",
                    bucket=bucket,
                    task_id=task["id"],
                    task=task,
                    prompt=_prompt_for_delivery(task, name),
                    version=task.get("version", 0),
                )

        for task in inbox.get("wbs_tasks") or []:
            if int(task.get("progress") or 0) >= 100:
                continue
            _emit_trigger(
                triggers=triggers,
                seen=seen,
                agent_name=name,
                source="wbs",
                bucket="wbs_open",
                task_id=task["wbs_id"],
                task=task,
                prompt=_prompt_for_wbs(task, name),
            )

    return triggers


def main() -> int:
    interval = max(15, int(_env("AGENT_RUNNER_INTERVAL_SEC", "60") or "60"))
    once = _env("AGENT_RUNNER_ONCE") in {"1", "true", "yes"}

    while True:
        state = _load_state()
        poll_once(state)
        _save_state(state)
        if once:
            break
        time.sleep(interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
