"""Agent Ops API views (TZ-complete)."""

from __future__ import annotations

import secrets
import time
import uuid

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from delivery.models import (
    AgentActionLog,
    AgentProfile,
    DeliveryAccessLog,
    DeliveryIdempotencyKey,
    DeliveryProjectMeta,
    DeliverySettings,
    DeliverySubTask,
    DeliveryTask,
    Epic,
    Sprint,
    TaskBlocker,
    TaskComment,
    TaskDependency,
    TaskFieldHistory,
    TaskGitHubReview,
    TaskMeaningChangeRequest,
    TaskStatusHistory,
)
from delivery.serializers import (
    AgentActionLogSerializer,
    AgentProfileSerializer,
    BlockerSerializer,
    CommentSerializer,
    DeliveryAccessLogSerializer,
    DeliveryProjectMetaSerializer,
    DeliverySettingsSerializer,
    DeliveryTaskSerializer,
    DeliveryTaskWriteSerializer,
    DependencySerializer,
    EpicSerializer,
    FieldHistorySerializer,
    HandoffSerializer,
    SprintSerializer,
    StatusHistorySerializer,
    SubTaskSerializer,
)
from delivery.services import (
    MEANING_FIELDS,
    agent_may_close_epic,
    assign_task,
    build_task_timeline,
    cancel_blocker,
    change_status,
    claim_task,
    create_handoff,
    log_agent_action,
    profile_may,
    record_field_changes,
    resolve_blocker,
    snapshot_task,
    would_create_dependency_cycle,
)
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin
from workspaces.models import WorkspaceAPIToken, WorkspaceMember

User = get_user_model()

RATE_LIMIT = 120
RATE_WINDOW = 60


class DeliveryOpsMixin(WorkspaceMixin):
    """TZ §9.1 — log every delivery API response for authenticated callers."""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            try:
                ws = self.get_workspace()
            except Exception:
                pass
        return response


def _ensure_ops_enabled(workspace):
    settings_row, _ = DeliverySettings.objects.get_or_create(workspace=workspace)
    if not settings_row.agent_ops_enabled:
        raise PermissionDenied("Agent Ops is disabled for this workspace.")
    return settings_row


def _agent_profile(workspace, user) -> AgentProfile | None:
    return AgentProfile.objects.filter(
        workspace=workspace, user=user, is_active=True
    ).first()


def _log_access(workspace, request, status_code: int = 0):
    if not request.user or not request.user.is_authenticated:
        return
    DeliveryAccessLog.objects.create(
        workspace=workspace,
        user=request.user,
        method=request.method,
        path=(request.path or "")[:255],
        status_code=status_code,
    )


def _can_mutate_task(workspace, user, task: DeliveryTask) -> bool:
    membership = WorkspaceMember.objects.filter(workspace=workspace, user=user).first()
    profile = _agent_profile(workspace, user)
    if profile and profile.role == "observer":
        return False
    if profile and profile.actor_type == AgentProfile.ActorType.AGENT:
        if task.project_id and profile.allowed_projects.exists():
            if not profile.allowed_projects.filter(pk=task.project_id).exists():
                return False
        if not (
            profile_may(profile, "write_task_own")
            or profile_may(profile, "write_task")
            or profile_may(profile, "claim")
            or profile_may(profile, "handoff")
            or profile_may(profile, "comment")
            or profile_may(profile, "blocker")
            or profile_may(profile, "review")
        ):
            return False
        if task.assignee_id and task.assignee_id != user.id:
            if task.assignee_role and profile.role != task.assignee_role:
                if task.status not in (
                    DeliveryTask.Status.READY,
                    DeliveryTask.Status.ASSIGNED,
                ):
                    return False
        return True
    if membership and membership.role in (
        WorkspaceMember.Role.OWNER,
        WorkspaceMember.Role.EDITOR,
    ):
        return True
    if not profile:
        return False
    if profile.role == "owner":
        return True
    if task.assignee_id == user.id:
        return True
    if task.assignee_role and task.assignee_role == profile.role:
        return True
    if task.status == DeliveryTask.Status.READY and task.assignee_role == profile.role:
        return True
    return False


def _require_action(workspace, user, action: str):
    profile = _agent_profile(workspace, user)
    if profile and profile.actor_type == AgentProfile.ActorType.AGENT:
        if not profile_may(profile, action):
            raise PermissionDenied(
                f"Agent role '{profile.role}' cannot perform '{action}'."
            )
    elif profile and not profile_may(profile, action) and profile.role == "observer":
        raise PermissionDenied("Observer is read-only.")


def _check_rate_limit(workspace_id: int, user_id: int):
    from django.core.cache import cache

    key = f"delivery:rl:{workspace_id}:{user_id}:{int(time.time()) // RATE_WINDOW}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT:
        raise ValidationError({"detail": "Rate limit exceeded. Try again later."})
    cache.set(key, count + 1, timeout=RATE_WINDOW + 5)


def _idempotency_get(workspace, user, request):
    key = request.headers.get("Idempotency-Key") or request.META.get(
        "HTTP_IDEMPOTENCY_KEY"
    )
    if not key:
        return None, None
    row = DeliveryIdempotencyKey.objects.filter(
        workspace=workspace, user=user, key=key[:128]
    ).first()
    if row:
        return key, Response(row.response_body, status=row.status_code)
    return key, None


def _idempotency_store(workspace, user, key, method, path, response: Response):
    if not key:
        return
    body = response.data if isinstance(response.data, dict) else {"data": response.data}
    DeliveryIdempotencyKey.objects.update_or_create(
        workspace=workspace,
        user=user,
        key=key[:128],
        defaults={
            "method": method,
            "path": path[:255],
            "status_code": response.status_code,
            "response_body": body,
        },
    )


class DeliverySettingsView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def patch(self, request):
        self.require_editor()
        row, _ = DeliverySettings.objects.get_or_create(
            workspace=self.get_workspace()
        )
        if "agent_ops_enabled" in request.data:
            row.agent_ops_enabled = bool(request.data.get("agent_ops_enabled"))
        if "github_webhook_secret" in request.data:
            row.github_webhook_secret = (
                request.data.get("github_webhook_secret") or ""
            )[:255]
        if "github_api_token" in request.data:
            row.github_api_token = (request.data.get("github_api_token") or "")[
                :255
            ]
        row.save()
        data = DeliverySettingsSerializer(row).data
        data["github_webhook_secret_set"] = bool(row.github_webhook_secret)
        data["github_api_token_set"] = bool(row.github_api_token)
        return Response(data)

    def get(self, request):
        row, _ = DeliverySettings.objects.get_or_create(
            workspace=self.get_workspace()
        )
        data = DeliverySettingsSerializer(row).data
        data["github_webhook_secret_set"] = bool(row.github_webhook_secret)
        data["github_api_token_set"] = bool(row.github_api_token)
        return Response(data)


class ProjectMetaListCreateView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        from projects.models import Project

        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        metas = {
            m.project_id: m
            for m in DeliveryProjectMeta.objects.filter(workspace=ws).select_related(
                "project", "project__manager"
            )
        }
        rows = []
        for project in Project.objects.filter(workspace=ws).select_related("manager"):
            meta = metas.get(project.id)
            rows.append(
                {
                    "id": meta.id if meta else None,
                    "project": project.id,
                    "project_name": project.name,
                    "description": project.description,
                    "status": project.status,
                    "owner": project.manager_id,
                    "owner_email": project.manager.email if project.manager_id else None,
                    "repo_url": meta.repo_url if meta else "",
                    "docs_url": meta.docs_url if meta else "",
                    "updated_at": meta.updated_at if meta else None,
                }
            )
        return Response(rows)

    def post(self, request):
        from projects.models import Project

        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        project_id = request.data.get("project")
        name = (request.data.get("name") or "").strip()
        if not project_id and not name:
            raise ValidationError({"project": "Provide project id or name to create"})
        if not project_id and name:
            project = Project.objects.create(
                workspace=ws,
                name=name[:255],
                description=(request.data.get("description") or "")[:5000],
                manager=request.user,
            )
            project_id = project.id
        row, _ = DeliveryProjectMeta.objects.update_or_create(
            workspace=ws,
            project_id=project_id,
            defaults={
                "repo_url": request.data.get("repo_url") or "",
                "docs_url": request.data.get("docs_url") or "",
            },
        )
        return Response(
            DeliveryProjectMetaSerializer(row).data, status=201
        )


class AgentProfileListCreateView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        rows = AgentProfile.objects.filter(workspace=ws).select_related("user")
        return Response(AgentProfileSerializer(rows, many=True).data)

    def post(self, request):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        ser = AgentProfileSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)
        project_ids = request.data.get("allowed_project_ids") or []
        row = AgentProfile.objects.create(workspace=ws, **data)
        if project_ids:
            row.allowed_projects.set(project_ids)
        log_agent_action(
            workspace=ws,
            user=request.user,
            action="agent_profile.create",
            entity_type="AgentProfile",
            entity_id=row.id,
        )
        return Response(AgentProfileSerializer(row).data, status=201)


class AgentServiceAccountCreateView(DeliveryOpsMixin, APIView):
    """TZ §9.1 / §15.4 — provision a dedicated agent user + API token."""

    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        role = (request.data.get("role") or "").strip()
        display_name = (request.data.get("display_name") or role or "agent").strip()
        if not role:
            raise ValidationError({"role": "Required"})
        suffix = uuid.uuid4().hex[:8]
        email = f"agent-{role}-{suffix}@agents.fastplan.local"
        username = f"agent_{role}_{suffix}"
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=secrets.token_urlsafe(32),
            )
            WorkspaceMember.objects.get_or_create(
                workspace=ws,
                user=user,
                defaults={"role": WorkspaceMember.Role.EDITOR},
            )
            token, raw = WorkspaceAPIToken.issue(
                workspace=ws,
                name=f"agent:{role}:{display_name}",
                scopes=["read", "write"],
                created_by=user,
            )
            profile = AgentProfile.objects.create(
                workspace=ws,
                user=user,
                role=role,
                actor_type=AgentProfile.ActorType.AGENT,
                display_name=display_name,
                is_service_account=True,
                api_token=token,
                allowed_actions=request.data.get("allowed_actions") or [],
            )
            project_ids = request.data.get("allowed_project_ids") or []
            if project_ids:
                profile.allowed_projects.set(project_ids)
        log_agent_action(
            workspace=ws,
            user=request.user,
            action="service_account.create",
            entity_type="AgentProfile",
            entity_id=profile.id,
            detail=display_name,
        )
        data = AgentProfileSerializer(profile).data
        data["api_token_raw"] = raw
        data["service_user_email"] = email
        return Response(data, status=201)


class AgentActionLogListView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        rows = AgentActionLog.objects.filter(workspace=ws)[:200]
        return Response(AgentActionLogSerializer(rows, many=True).data)


class AccessLogListView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        self.require_editor()
        rows = DeliveryAccessLog.objects.filter(workspace=ws)[:200]
        return Response(DeliveryAccessLogSerializer(rows, many=True).data)


class EpicListCreateView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        rows = Epic.objects.filter(workspace=ws)
        return Response(EpicSerializer(rows, many=True).data)

    def post(self, request):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        ser = EpicSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        profile = _agent_profile(ws, request.user)
        data = dict(ser.validated_data)
        data.pop("task_ids", None)
        if (
            profile
            and profile.actor_type == AgentProfile.ActorType.AGENT
            and profile.role not in ("owner", "planner", "documentation")
        ):
            data["priority"] = Epic.Priority.NORMAL
        row = Epic.objects.create(workspace=ws, **data)
        return Response(EpicSerializer(row).data, status=201)


class EpicDetailView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def patch(self, request, epic_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        epic = get_object_or_404(Epic.objects.filter(workspace=ws), pk=epic_id)
        profile = _agent_profile(ws, request.user)
        if (
            profile
            and profile.actor_type == AgentProfile.ActorType.AGENT
            and profile.role not in ("owner", "planner")
            and "priority" in request.data
        ):
            raise PermissionDenied("Delivery agents cannot change epic priority.")
        new_status = request.data.get("status")
        if new_status in (Epic.Status.DONE, Epic.Status.ARCHIVED):
            if not agent_may_close_epic(profile):
                raise PermissionDenied("Delivery agents cannot close an epic.")
        ser = EpicSerializer(epic, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        for k, v in ser.validated_data.items():
            if k == "task_ids":
                continue
            setattr(epic, k, v)
        epic.save()
        return Response(EpicSerializer(epic).data)


class SprintListCreateView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        rows = Sprint.objects.filter(workspace=ws)
        return Response(SprintSerializer(rows, many=True).data)

    def post(self, request):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        ser = SprintSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = {
            k: v
            for k, v in ser.validated_data.items()
            if k not in ("task_count", "task_ids")
        }
        row = Sprint.objects.create(workspace=ws, **data)
        return Response(SprintSerializer(row).data, status=201)


class SprintDetailView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def patch(self, request, sprint_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        sprint = get_object_or_404(Sprint.objects.filter(workspace=ws), pk=sprint_id)
        ser = SprintSerializer(sprint, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        for k, v in ser.validated_data.items():
            if k in ("task_count", "task_ids"):
                continue
            setattr(sprint, k, v)
        sprint.save()
        return Response(SprintSerializer(sprint).data)


class TaskListCreateView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        qs = DeliveryTask.objects.filter(workspace=ws).select_related(
            "assignee", "epic", "sprint"
        )
        status_q = request.query_params.get("status")
        role_q = request.query_params.get("role") or request.query_params.get(
            "assignee_role"
        )
        sprint_q = request.query_params.get("sprint")
        epic_q = request.query_params.get("epic")
        mine = request.query_params.get("mine")
        ready_only = request.query_params.get("ready")
        if status_q:
            qs = qs.filter(status=status_q)
        if role_q:
            qs = qs.filter(assignee_role=role_q)
        if sprint_q:
            qs = qs.filter(sprint_id=sprint_q)
        if epic_q:
            qs = qs.filter(epic_id=epic_q)
        if mine in ("1", "true", "yes"):
            qs = qs.filter(assignee=request.user)
        if ready_only in ("1", "true", "yes"):
            qs = qs.filter(status=DeliveryTask.Status.READY)
        profile = _agent_profile(ws, request.user)
        if (
            profile
            and profile.actor_type == AgentProfile.ActorType.AGENT
            and profile.role not in ("owner", "observer", "planner", "documentation")
            and not any([status_q, role_q, mine, ready_only])
        ):
            qs = qs.filter(assignee_role=profile.role)
        return Response(DeliveryTaskSerializer(qs[:300], many=True).data)

    def post(self, request):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        _check_rate_limit(ws.id, request.user.id)
        idem_key, cached = _idempotency_get(ws, request.user, request)
        if cached:
            return cached
        ser = DeliveryTaskWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        task = DeliveryTask.objects.create(
            workspace=ws, created_by=request.user, **ser.validated_data
        )
        TaskStatusHistory.objects.create(
            task=task,
            from_status="",
            to_status=task.status,
            changed_by=request.user,
            reason="created",
        )
        log_agent_action(
            workspace=ws,
            user=request.user,
            action="task.create",
            entity_type="DeliveryTask",
            entity_id=task.id,
        )
        resp = Response(DeliveryTaskSerializer(task).data, status=201)
        _idempotency_store(ws, request.user, idem_key, "POST", request.path, resp)
        return resp


class TaskDetailView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, task_id):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(
            DeliveryTask.objects.filter(workspace=ws).prefetch_related(
                "subtasks", "blockers", "handoffs", "dependencies"
            ),
            pk=task_id,
        )
        return Response(DeliveryTaskSerializer(task).data)

    def patch(self, request, task_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        _check_rate_limit(ws.id, request.user.id)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        if not _can_mutate_task(ws, request.user, task):
            raise PermissionDenied("Not allowed to mutate this task.")
        profile = _agent_profile(ws, request.user)
        meaning_request = None
        data = dict(request.data)
        if (
            profile
            and profile.actor_type == AgentProfile.ActorType.AGENT
            and profile.role not in ("owner", "planner")
        ):
            touched = MEANING_FIELDS.intersection(data.keys())
            if touched:
                proposed = {k: data.pop(k) for k in list(touched)}
                meaning_request = TaskMeaningChangeRequest.objects.create(
                    task=task,
                    requested_by=request.user,
                    proposed_fields=proposed,
                    note=(request.data.get("meaning_note") or "")[:2000],
                )
                TaskComment.objects.create(
                    task=task,
                    kind=TaskComment.Kind.OWNER_REQUEST,
                    body=(
                        "Meaning change awaiting Owner/Planner approval "
                        f"(#{meaning_request.id}): "
                        + ", ".join(sorted(proposed.keys()))
                    ),
                    author=request.user,
                )
                log_agent_action(
                    workspace=ws,
                    user=request.user,
                    action="meaning.request",
                    entity_type="TaskMeaningChangeRequest",
                    entity_id=meaning_request.id,
                )
        before = snapshot_task(task)
        ser = DeliveryTaskWriteSerializer(task, data=data, partial=True)
        ser.is_valid(raise_exception=True)
        for k, v in ser.validated_data.items():
            setattr(task, k, v)
        task.version += 1
        task.save()
        record_field_changes(
            task, user=request.user, before=before, after=snapshot_task(task)
        )
        payload = DeliveryTaskSerializer(task).data
        if meaning_request:
            payload["meaning_change_request_id"] = meaning_request.id
            payload["meaning_change_pending"] = True
        return Response(payload)


class MeaningChangeListView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, task_id):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        rows = task.meaning_change_requests.all()[:50]
        return Response(
            [
                {
                    "id": r.id,
                    "status": r.status,
                    "proposed_fields": r.proposed_fields,
                    "note": r.note,
                    "requested_by": r.requested_by_id,
                    "reviewed_by": r.reviewed_by_id,
                    "review_note": r.review_note,
                    "created_at": r.created_at,
                    "reviewed_at": r.reviewed_at,
                }
                for r in rows
            ]
        )


class MeaningChangeReviewView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, task_id, request_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        profile = _agent_profile(ws, request.user)
        membership = WorkspaceMember.objects.filter(
            workspace=ws, user=request.user
        ).first()
        is_ownerish = membership and membership.role == WorkspaceMember.Role.OWNER
        if not (
            is_ownerish
            or (profile and profile.role in ("owner", "planner"))
        ):
            raise PermissionDenied("Only Owner/Planner can approve meaning changes.")
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        row = get_object_or_404(task.meaning_change_requests.all(), pk=request_id)
        if row.status != TaskMeaningChangeRequest.Status.PENDING:
            raise ValidationError({"detail": "Request already reviewed"})
        decision = (request.data.get("decision") or "approve").strip().lower()
        from django.utils import timezone as dj_tz

        row.reviewed_by = request.user
        row.reviewed_at = dj_tz.now()
        row.review_note = (request.data.get("note") or "")[:2000]
        if decision in ("reject", "rejected"):
            row.status = TaskMeaningChangeRequest.Status.REJECTED
            row.save()
            return Response({"id": row.id, "status": row.status})
        before = snapshot_task(task)
        for field, value in (row.proposed_fields or {}).items():
            if hasattr(task, field):
                setattr(task, field, value)
        task.version += 1
        task.save()
        record_field_changes(
            task, user=request.user, before=before, after=snapshot_task(task)
        )
        row.status = TaskMeaningChangeRequest.Status.APPROVED
        row.save()
        TaskComment.objects.create(
            task=task,
            kind=TaskComment.Kind.COMMENT,
            body=f"Meaning change #{row.id} approved by Owner/Planner",
            author=request.user,
        )
        return Response(
            {
                "id": row.id,
                "status": row.status,
                "task": DeliveryTaskSerializer(task).data,
            }
        )


class TaskStatusView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, task_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        _check_rate_limit(ws.id, request.user.id)
        idem_key, cached = _idempotency_get(ws, request.user, request)
        if cached:
            return cached
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        if not _can_mutate_task(ws, request.user, task):
            raise PermissionDenied("Not allowed to mutate this task.")
        to_status = (request.data.get("status") or "").strip()
        reason = (request.data.get("reason") or "").strip()
        try:
            change_status(task, to_status=to_status, user=request.user, reason=reason)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        task.refresh_from_db()
        resp = Response(DeliveryTaskSerializer(task).data)
        _idempotency_store(ws, request.user, idem_key, "POST", request.path, resp)
        return resp


class TaskClaimView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, task_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        _require_action(ws, request.user, "claim")
        _check_rate_limit(ws.id, request.user.id)
        idem_key, cached = _idempotency_get(ws, request.user, request)
        if cached:
            return cached
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        expected = request.data.get("version")
        try:
            expected_i = int(expected) if expected is not None else None
        except (TypeError, ValueError):
            expected_i = None
        try:
            claimed = claim_task(
                task, user=request.user, expected_version=expected_i
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        log_agent_action(
            workspace=ws,
            user=request.user,
            action="task.claim",
            entity_type="DeliveryTask",
            entity_id=claimed.id,
        )
        resp = Response(DeliveryTaskSerializer(claimed).data)
        _idempotency_store(ws, request.user, idem_key, "POST", request.path, resp)
        return resp


class TaskAssignView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, task_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        _require_action(ws, request.user, "assign")
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        assignee = request.data.get("assignee", None)
        role = request.data.get("assignee_role")
        try:
            assigned = assign_task(
                task,
                user=request.user,
                assignee_id=assignee,
                assignee_role=role,
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        log_agent_action(
            workspace=ws,
            user=request.user,
            action="task.assign",
            entity_type="DeliveryTask",
            entity_id=assigned.id,
            detail=str(assignee),
        )
        return Response(DeliveryTaskSerializer(assigned).data)


class TaskHistoryView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, task_id):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(
            DeliveryTask.objects.filter(workspace=ws).prefetch_related(
                "status_history",
                "field_history",
                "handoffs",
                "blockers",
                "comments",
            ),
            pk=task_id,
        )
        status_rows = task.status_history.all()
        field_rows = task.field_history.all()[:200]
        return Response(
            {
                "status_history": StatusHistorySerializer(status_rows, many=True).data,
                "field_history": FieldHistorySerializer(field_rows, many=True).data,
                "timeline": build_task_timeline(task),
            }
        )


class TaskBlockerListCreateView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, task_id):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        return Response(BlockerSerializer(task.blockers.all(), many=True).data)

    def post(self, request, task_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        title = (request.data.get("title") or "").strip()
        if not title:
            raise ValidationError({"title": "Required"})
        blocker = TaskBlocker.objects.create(
            task=task,
            title=title,
            detail=(request.data.get("detail") or ""),
            needs_owner_decision=bool(request.data.get("needs_owner_decision")),
            created_by=request.user,
        )
        TaskComment.objects.create(
            task=task,
            kind=TaskComment.Kind.BLOCKER_NOTE,
            body=f"Blocker: {title}",
            author=request.user,
        )
        log_agent_action(
            workspace=ws,
            user=request.user,
            action="blocker.create",
            entity_type="TaskBlocker",
            entity_id=blocker.id,
        )
        if task.status != DeliveryTask.Status.BLOCKED:
            try:
                change_status(
                    task,
                    to_status=DeliveryTask.Status.BLOCKED,
                    user=request.user,
                    reason=f"blocker: {title}",
                )
            except ValueError:
                pass
        return Response(BlockerSerializer(blocker).data, status=201)


class TaskBlockerResolveView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, task_id, blocker_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        blocker = get_object_or_404(task.blockers.all(), pk=blocker_id)
        note = (request.data.get("note") or "").strip()
        resolve_blocker(blocker, user=request.user, note=note)
        blocker.refresh_from_db()
        return Response(BlockerSerializer(blocker).data)


class TaskBlockerCancelView(DeliveryOpsMixin, APIView):
    """Soft-cancel with required reason — no hard delete (TZ §12)."""

    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, task_id, blocker_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        blocker = get_object_or_404(task.blockers.all(), pk=blocker_id)
        reason = (request.data.get("reason") or "").strip()
        try:
            cancel_blocker(blocker, user=request.user, reason=reason)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        blocker.refresh_from_db()
        return Response(BlockerSerializer(blocker).data)


class TaskHandoffCreateView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, task_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        _check_rate_limit(ws.id, request.user.id)
        idem_key, cached = _idempotency_get(ws, request.user, request)
        if cached:
            return cached
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        if not _can_mutate_task(ws, request.user, task):
            raise PermissionDenied("Not allowed to hand off this task.")
        _require_action(ws, request.user, "handoff")
        try:
            handoff = create_handoff(
                task,
                user=request.user,
                from_role=(request.data.get("from_role") or task.assignee_role or ""),
                to_role=(request.data.get("to_role") or ""),
                done_summary=(request.data.get("done_summary") or ""),
                left_summary=(request.data.get("left_summary") or ""),
                branch_or_pr_url=(request.data.get("branch_or_pr_url") or ""),
                checks_url=(request.data.get("checks_url") or ""),
                open_questions=(request.data.get("open_questions") or ""),
                needs_owner_decision=bool(request.data.get("needs_owner_decision")),
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        task.refresh_from_db()
        resp = Response(
            {
                "handoff": HandoffSerializer(handoff).data,
                "task": DeliveryTaskSerializer(task).data,
            },
            status=201,
        )
        _idempotency_store(ws, request.user, idem_key, "POST", request.path, resp)
        return resp


class TaskCommentListCreateView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, task_id):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        return Response(CommentSerializer(task.comments.all(), many=True).data)

    def post(self, request, task_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        _require_action(ws, request.user, "comment")
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        body = (request.data.get("body") or "").strip()
        if not body:
            raise ValidationError({"body": "Required"})
        kind = request.data.get("kind") or TaskComment.Kind.COMMENT
        row = TaskComment.objects.create(
            task=task, body=body, kind=kind, author=request.user
        )
        return Response(CommentSerializer(row).data, status=201)


class TaskSubTaskListCreateView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, task_id):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        return Response(SubTaskSerializer(task.subtasks.all(), many=True).data)

    def post(self, request, task_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        title = (request.data.get("title") or "").strip()
        if not title:
            raise ValidationError({"title": "Required"})
        row = DeliverySubTask.objects.create(
            task=task,
            title=title,
            expected_artifact=(request.data.get("expected_artifact") or ""),
            assignee_id=request.data.get("assignee"),
            status=request.data.get("status") or DeliverySubTask.Status.TODO,
        )
        return Response(SubTaskSerializer(row).data, status=201)


class TaskSubTaskDetailView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def patch(self, request, task_id, subtask_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        row = get_object_or_404(task.subtasks.all(), pk=subtask_id)
        for field in ("title", "status", "expected_artifact"):
            if field in request.data:
                setattr(row, field, request.data.get(field) or getattr(row, field))
        if "assignee" in request.data:
            row.assignee_id = request.data.get("assignee")
        row.save()
        return Response(SubTaskSerializer(row).data)


class TaskDependencyListCreateView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, task_id):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        return Response(DependencySerializer(task.dependencies.all(), many=True).data)

    def post(self, request, task_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        depends_on_id = request.data.get("depends_on")
        if not depends_on_id:
            raise ValidationError({"depends_on": "Required"})
        if int(depends_on_id) == task.id:
            raise ValidationError({"depends_on": "Task cannot depend on itself"})
        if would_create_dependency_cycle(task.id, int(depends_on_id)):
            raise ValidationError({"depends_on": "Dependency would create a cycle"})
        other = get_object_or_404(
            DeliveryTask.objects.filter(workspace=ws), pk=depends_on_id
        )
        dep, created = TaskDependency.objects.get_or_create(
            task=task, depends_on=other
        )
        return Response(
            DependencySerializer(dep).data, status=201 if created else 200
        )


class TaskPrSnippetView(DeliveryOpsMixin, APIView):
    """TZ §10 — markdown to paste into PR body linking back to the task."""

    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, task_id):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        base = request.build_absolute_uri("/").rstrip("/")
        snippet = (
            f"## Fast Plan task\n"
            f"- Task: [{task.title}]({base}/agent-ops?task={task.id})\n"
            f"- Role: `{task.assignee_role or '—'}`\n"
            f"- DoD: {task.done_criterion or '—'}\n"
        )
        return Response({"markdown": snippet, "task_id": task.id})


class TaskPrAttachView(DeliveryOpsMixin, APIView):
    """TZ §10 desirable — append task link snippet to GitHub PR body via PAT."""

    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, task_id):
        import json
        import urllib.error
        import urllib.request

        self.require_editor()
        ws = self.get_workspace()
        settings_row = _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        token = (settings_row.github_api_token or "").strip()
        if not token:
            raise ValidationError(
                {"github_api_token": "Set DeliverySettings.github_api_token first"}
            )
        repo = (request.data.get("repo") or task.github_repo or "").strip()
        pr_number = request.data.get("pr_number") or task.github_pr_number
        if not repo or not pr_number:
            raise ValidationError(
                {"detail": "Task needs github_repo and github_pr_number (or pass them)"}
            )
        base = request.build_absolute_uri("/").rstrip("/")
        snippet = (
            f"\n\n## Fast Plan task\n"
            f"- Task: [{task.title}]({base}/agent-ops?task={task.id})\n"
            f"- Role: `{task.assignee_role or '—'}`\n"
            f"- DoD: {task.done_criterion or '—'}\n"
        )
        api_url = f"https://api.github.com/repos/{repo}/pulls/{int(pr_number)}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "fast-plan-agent-ops",
        }
        try:
            req = urllib.request.Request(api_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=20) as resp:
                current = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            raise ValidationError(
                {"detail": f"GitHub GET PR failed: {exc.code}"}
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise ValidationError({"detail": f"GitHub GET PR failed: {exc}"}) from exc
        body = current.get("body") or ""
        marker = f"/agent-ops?task={task.id}"
        if marker in body:
            return Response(
                {
                    "ok": True,
                    "skipped": True,
                    "detail": "Task link already present in PR body",
                    "pr_url": current.get("html_url") or task.github_pr_url,
                }
            )
        new_body = body + snippet
        payload = json.dumps({"body": new_body}).encode()
        try:
            req = urllib.request.Request(
                api_url,
                data=payload,
                headers={**headers, "Content-Type": "application/json"},
                method="PATCH",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                updated = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            raise ValidationError(
                {"detail": f"GitHub PATCH PR failed: {exc.code}"}
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise ValidationError({"detail": f"GitHub PATCH PR failed: {exc}"}) from exc
        task.github_pr_url = updated.get("html_url") or task.github_pr_url
        task.github_pr_number = int(pr_number)
        task.github_repo = repo
        task.github_pr_state = updated.get("state") or task.github_pr_state
        task.save(
            update_fields=[
                "github_pr_url",
                "github_pr_number",
                "github_repo",
                "github_pr_state",
            ]
        )
        log_agent_action(
            workspace=ws,
            user=request.user,
            action="github.attach_pr",
            entity_type="DeliveryTask",
            entity_id=task.id,
        )
        return Response(
            {
                "ok": True,
                "skipped": False,
                "pr_url": task.github_pr_url,
                "task": DeliveryTaskSerializer(task).data,
            }
        )


class AgentQueueView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        profile = _agent_profile(ws, request.user)
        role = request.query_params.get("role") or (
            profile.role if profile else ""
        )
        qs = DeliveryTask.objects.filter(workspace=ws).select_related("assignee")
        if role:
            qs = qs.filter(assignee_role=role)
        status_q = request.query_params.get("status") or DeliveryTask.Status.READY
        qs = qs.filter(status=status_q)
        return Response(DeliveryTaskSerializer(qs[:100], many=True).data)


def _verify_github_signature(request, secrets_needed: set[str]) -> bool:
    import hashlib
    import hmac

    if not secrets_needed:
        return True
    signature = request.headers.get("X-Hub-Signature-256") or request.META.get(
        "HTTP_X_HUB_SIGNATURE_256", ""
    )
    raw = getattr(request, "_request", request).body or b""
    for secret in secrets_needed:
        digest = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        expected = f"sha256={digest}"
        if hmac.compare_digest(expected, signature):
            return True
    return False


def _find_github_tasks(full_name: str, number, head: str) -> list[DeliveryTask]:
    tasks = list(
        DeliveryTask.objects.filter(
            github_repo=full_name, github_pr_number=number
        ).select_related("workspace")
    )
    if tasks or not head:
        return tasks
    return list(
        DeliveryTask.objects.filter(
            github_repo=full_name,
            github_branch=head,
            github_pr_number__isnull=True,
        ).select_related("workspace")
    )


def _upsert_github_review(task: DeliveryTask, review: dict, comment: dict, event: str):
    notes = []
    if review.get("body") or review.get("state"):
        state = (review.get("state") or "commented").lower()
        mapped = {
            "approved": TaskGitHubReview.State.APPROVED,
            "changes_requested": TaskGitHubReview.State.CHANGES_REQUESTED,
            "dismissed": TaskGitHubReview.State.DISMISSED,
            "commented": TaskGitHubReview.State.COMMENTED,
        }.get(state, TaskGitHubReview.State.OPEN)
        gh_id = review.get("id")
        author = ((review.get("user") or {}).get("login") or "")[:255]
        defaults = {
            "author_login": author,
            "state": mapped,
            "body": (review.get("body") or "")[:10000],
            "html_url": (review.get("html_url") or "")[:500],
            "is_resolved": mapped
            in (
                TaskGitHubReview.State.APPROVED,
                TaskGitHubReview.State.DISMISSED,
            ),
        }
        if gh_id:
            TaskGitHubReview.objects.update_or_create(
                task=task,
                github_review_id=gh_id,
                defaults=defaults,
            )
        else:
            TaskGitHubReview.objects.create(task=task, **defaults)
        if review.get("body"):
            notes.append(f"[{state}] {review.get('body')}")
    if comment.get("body") and event in (
        "pull_request_review_comment",
        "issue_comment",
        "",
    ):
        TaskGitHubReview.objects.create(
            task=task,
            author_login=((comment.get("user") or {}).get("login") or "")[:255],
            state=TaskGitHubReview.State.OPEN,
            body=(comment.get("body") or "")[:10000],
            html_url=(comment.get("html_url") or "")[:500],
        )
        notes.append(comment.get("body"))
    return notes


class GitHubWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        action = payload.get("action") or ""
        event = request.headers.get("X-GitHub-Event") or request.META.get(
            "HTTP_X_GITHUB_EVENT", ""
        )
        pr = payload.get("pull_request") or {}
        repo = payload.get("repository") or {}
        full_name = repo.get("full_name") or ""
        number = pr.get("number") or (payload.get("issue") or {}).get("number")
        state = pr.get("state") or ""
        html_url = pr.get("html_url") or ""
        head = (pr.get("head") or {}).get("ref") or ""
        sha = (pr.get("head") or {}).get("sha") or ""
        review = payload.get("review") or {}
        comment = payload.get("comment") or {}
        if not full_name or not number:
            return Response({"detail": "ignored"}, status=200)
        tasks = _find_github_tasks(full_name, number, head)
        if not tasks:
            return Response({"ok": True, "updated": 0, "action": action})
        secrets_needed = {
            DeliverySettings.objects.filter(workspace_id=t.workspace_id)
            .values_list("github_webhook_secret", flat=True)
            .first()
            or ""
            for t in tasks
        }
        secrets_needed.discard("")
        if not _verify_github_signature(request, secrets_needed):
            return Response({"detail": "Invalid signature"}, status=401)
        updated = 0
        for task in tasks:
            if pr:
                task.github_pr_state = state or task.github_pr_state
                task.github_pr_url = html_url or task.github_pr_url
                task.github_pr_number = number or task.github_pr_number
                if head:
                    task.github_branch = head
                if sha:
                    task.github_commit = sha[:64]
                if action in ("synchronize", "opened", "reopened", "closed"):
                    task.github_checks_status = state
            notes = _upsert_github_review(task, review, comment, event)
            if notes:
                existing = task.github_review_notes or ""
                addition = "\n---\n".join(notes)
                task.github_review_notes = (
                    f"{existing}\n{addition}".strip()
                    if existing
                    else addition
                )
            task.save()
            updated += 1
        return Response({"ok": True, "updated": updated, "action": action})


class OverviewView(DeliveryOpsMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        from delivery.models import TaskHandoff

        ws = self.get_workspace()
        settings_row, _ = DeliverySettings.objects.get_or_create(workspace=ws)
        if not settings_row.agent_ops_enabled:
            return Response(
                {
                    "agent_ops_enabled": False,
                    "blocked": [],
                    "stuck_review": [],
                    "awaiting_owner": [],
                    "returned_from_qa": [],
                }
            )
        tasks = DeliveryTask.objects.filter(workspace=ws)
        blocked = tasks.filter(status=DeliveryTask.Status.BLOCKED)[:50]
        review = tasks.filter(status=DeliveryTask.Status.REVIEW)[:50]
        awaiting_items = []
        for b in TaskBlocker.objects.filter(
            task__workspace=ws,
            needs_owner_decision=True,
            resolved_at__isnull=True,
            cancelled_at__isnull=True,
        ).select_related("task")[:50]:
            awaiting_items.append(
                {
                    "blocker_id": b.id,
                    "title": b.title,
                    "task_id": b.task_id,
                    "task_title": b.task.title,
                    "source": "blocker",
                }
            )
        for h in TaskHandoff.objects.filter(
            task__workspace=ws, needs_owner_decision=True
        ).select_related("task")[:50]:
            awaiting_items.append(
                {
                    "blocker_id": None,
                    "title": f"Handoff {h.from_role}→{h.to_role}",
                    "task_id": h.task_id,
                    "task_title": h.task.title,
                    "source": "handoff",
                }
            )
        for c in TaskComment.objects.filter(
            task__workspace=ws, kind=TaskComment.Kind.OWNER_REQUEST
        ).select_related("task")[:30]:
            awaiting_items.append(
                {
                    "blocker_id": None,
                    "title": c.body[:120],
                    "task_id": c.task_id,
                    "task_title": c.task.title,
                    "source": "owner_request",
                }
            )
        for m in TaskMeaningChangeRequest.objects.filter(
            task__workspace=ws,
            status=TaskMeaningChangeRequest.Status.PENDING,
        ).select_related("task")[:30]:
            awaiting_items.append(
                {
                    "blocker_id": None,
                    "title": f"Meaning change #{m.id}: "
                    + ", ".join(sorted((m.proposed_fields or {}).keys())),
                    "task_id": m.task_id,
                    "task_title": m.task.title,
                    "source": "meaning_change",
                }
            )
        returned_ids = (
            TaskStatusHistory.objects.filter(
                task__workspace=ws,
                from_status=DeliveryTask.Status.QA,
                to_status=DeliveryTask.Status.IN_PROGRESS,
            )
            .values_list("task_id", flat=True)
            .distinct()[:50]
        )
        returned = tasks.filter(pk__in=returned_ids)
        return Response(
            {
                "agent_ops_enabled": True,
                "blocked": DeliveryTaskSerializer(blocked, many=True).data,
                "stuck_review": DeliveryTaskSerializer(review, many=True).data,
                "awaiting_owner": awaiting_items[:80],
                "returned_from_qa": DeliveryTaskSerializer(returned, many=True).data,
            }
        )
