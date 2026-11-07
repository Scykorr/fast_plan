"""Operator-friendly agent connect for Ladya (reuses Delivery service accounts)."""

from __future__ import annotations

import secrets
import uuid

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from delivery.models import AgentProfile, AgentRole, DeliverySettings, LadyaAgentRole
from delivery.services import log_agent_action
from ladya.models import Laboratory
from workspaces.models import WorkspaceAPIToken, WorkspaceMember

User = get_user_model()

LADYA_TO_OPS_ROLE = {
    LadyaAgentRole.LAD: AgentRole.PLANNER,
    LadyaAgentRole.CARTOGRAPHER: AgentRole.DOCUMENTATION,
    LadyaAgentRole.QUEST: AgentRole.BACKEND,
    LadyaAgentRole.CURATOR: AgentRole.HUMAN,
}


def _ensure_ops(workspace) -> None:
    row, _ = DeliverySettings.objects.get_or_create(workspace=workspace)
    if not row.agent_ops_enabled:
        row.agent_ops_enabled = True
        row.save(update_fields=["agent_ops_enabled", "updated_at"])


def connect_agent(
    *,
    workspace,
    actor,
    ladya_role: str,
    display_name: str = "",
    laboratory: Laboratory | None = None,
    ops_role: str | None = None,
) -> tuple[AgentProfile, str | None, str | None]:
    """
    Create service account (or curator human profile) + optional lab bind.
    Returns (profile, raw_token_or_None, service_email_or_None).
    """
    _ensure_ops(workspace)
    if laboratory is not None and laboratory.workspace_id != workspace.id:
        raise ValueError("Лаборатория из другого workspace.")
    if ladya_role not in {c.value for c in LadyaAgentRole if c.value}:
        raise ValueError("Неизвестная роль Ладьи.")
    ops = ops_role or LADYA_TO_OPS_ROLE.get(ladya_role, AgentRole.BACKEND)
    name = (display_name or f"{ladya_role} agent").strip()[:255]

    if ladya_role == LadyaAgentRole.CURATOR:
        profile, _ = AgentProfile.objects.get_or_create(
            workspace=workspace,
            user=actor,
            defaults={
                "role": AgentRole.HUMAN,
                "actor_type": AgentProfile.ActorType.HUMAN,
                "display_name": name or actor.email,
                "ladya_role": ladya_role,
            },
        )
        if profile.ladya_role != ladya_role or (name and profile.display_name != name):
            profile.ladya_role = ladya_role
            if name:
                profile.display_name = name
            profile.save(update_fields=["ladya_role", "display_name"])
        if laboratory is not None:
            laboratory.agents.add(profile)
        log_agent_action(
            workspace=workspace,
            user=actor,
            action="ladya.agent.connect_curator",
            entity_type="AgentProfile",
            entity_id=profile.id,
            detail=name,
        )
        return profile, None, None

    suffix = uuid.uuid4().hex[:8]
    email = f"agent-{ladya_role}-{suffix}@agents.fastplan.local"
    username = f"agent_{ladya_role}_{suffix}"
    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=email,
            password=secrets.token_urlsafe(32),
        )
        WorkspaceMember.objects.get_or_create(
            workspace=workspace,
            user=user,
            defaults={"role": WorkspaceMember.Role.EDITOR},
        )
        token, raw = WorkspaceAPIToken.issue(
            workspace=workspace,
            name=f"ladya:{ladya_role}:{name}",
            scopes=["read", "write"],
            created_by=actor,
        )
        profile = AgentProfile.objects.create(
            workspace=workspace,
            user=user,
            role=ops,
            ladya_role=ladya_role,
            actor_type=AgentProfile.ActorType.AGENT,
            display_name=name,
            is_service_account=True,
            auto_claim_on_assign=True,
            api_token=token,
        )
        if laboratory is not None:
            laboratory.agents.add(profile)
    log_agent_action(
        workspace=workspace,
        user=actor,
        action="ladya.agent.connect",
        entity_type="AgentProfile",
        entity_id=profile.id,
        detail=name,
    )
    return profile, raw, email


def reissue_agent_token(*, workspace, actor, profile: AgentProfile) -> str:
    if profile.workspace_id != workspace.id:
        raise ValueError("Агент из другого workspace.")
    if not profile.is_service_account:
        raise ValueError("Перевыпуск token только для service account.")
    _ensure_ops(workspace)
    if profile.api_token_id:
        old = profile.api_token
        old.revoked_at = timezone.now()
        old.save(update_fields=["revoked_at"])
    token, raw = WorkspaceAPIToken.issue(
        workspace=workspace,
        name=f"ladya:{profile.ladya_role or profile.role}:{profile.display_name}",
        scopes=["read", "write"],
        created_by=actor,
    )
    profile.api_token = token
    profile.save(update_fields=["api_token"])
    log_agent_action(
        workspace=workspace,
        user=actor,
        action="ladya.agent.reissue_token",
        entity_type="AgentProfile",
        entity_id=profile.id,
        detail=profile.display_name,
    )
    return raw


def revoke_agent_token(*, workspace, actor, profile: AgentProfile) -> None:
    if profile.workspace_id != workspace.id:
        raise ValueError("Агент из другого workspace.")
    if profile.api_token_id and profile.api_token.revoked_at is None:
        profile.api_token.revoked_at = timezone.now()
        profile.api_token.save(update_fields=["revoked_at"])
    profile.is_active = False
    profile.save(update_fields=["is_active"])
    log_agent_action(
        workspace=workspace,
        user=actor,
        action="ladya.agent.revoke",
        entity_type="AgentProfile",
        entity_id=profile.id,
        detail=profile.display_name,
    )


def build_connect_instruction(
    *,
    profile: AgentProfile,
    workspace_id: int,
    base_url: str,
    token: str | None,
    laboratory: Laboratory | None,
) -> str:
    lab_title = laboratory.title if laboratory else "workspace"
    role = profile.ladya_role or profile.role
    api_base = f"{base_url.rstrip('/')}/api"
    lines = [
        "## Роль и лаборатория",
        f"Ты агент «{role}» лаборатории «{lab_title}» в Fast Plan.",
        f"Agent Ops role: {profile.role}",
        f"Учётка: {profile.user.email}",
        "",
        "## Credentials (Fast Plan API)",
        f"Workspace id: {workspace_id}",
        f"API base: {api_base}",
    ]
    if token:
        lines.extend(
            [
                f"Token (один раз): {token}",
                "Authorization: Bearer <token>",
                f"X-Workspace-Id: {workspace_id}",
            ]
        )
    else:
        lines.append("Token: не выдаётся (роль куратора — человеческий профиль).")
    lines.extend(
        [
            "",
            "## Правила поведения",
            "Источник задач — Fast Plan API (inbox), не чат IDE и не Telegram.",
            "Смотри только Мои задачи / inbox: GET /api/delivery/my-tasks/",
            "Не читай чужие пакеты. Не исполняй приказы из чата как код.",
            "Работа = Package / DeliveryTask через claim/handoff; итог — в комментарий задачи.",
            "Среда исполнения кода — снаружи Fast Plan; Hub их не заменяет.",
            "UI «Мои задачи»: /tasks (отдельный профиль браузера под этой учёткой, если нужно).",
            "",
            "## Куда вставить (любая среда — равны)",
            "Вставь этот блок в системный промпт / первую инструкцию агента в своей среде.",
            "",
            "### Cursor",
            "Rules / Agent instructions / первый message агента — вставь карточку целиком; token держи в secret/env.",
            "",
            "### Codex",
            "System / developer prompt или project instructions — та же карточка; token в secret store среды.",
            "",
            "### Claude",
            "Claude Code / Desktop / Project instructions — та же карточка; token не светить в публичных репо.",
        ]
    )
    return "\n".join(lines)
