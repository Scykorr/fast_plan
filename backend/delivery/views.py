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
    cancel_blocker,
    change_status,
    claim_task,
    create_handoff,
    log_agent_action,
    record_field_changes,
    resolve_blocker,
    snapshot_task,
)
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin
from workspaces.models import WorkspaceAPIToken, WorkspaceMember

User = get_user_model()

RATE_LIMIT = 120
RATE_WINDOW = 60


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
    if membership and membership.role in (
        WorkspaceMember.Role.OWNER,
        WorkspaceMember.Role.EDITOR,
    ):
        if profile and profile.actor_type == AgentProfile.ActorType.AGENT:
            if profile.role == "observer":
                return False
            if task.project_id and profile.allowed_projects.exists():
                if not profile.allowed_projects.filter(pk=task.project_id).exists():
                    return False
            if task.assignee_id and task.assignee_id != user.id:
                if task.assignee_role and profile.role != task.assignee_role:
                    if task.status not in (
                        DeliveryTask.Status.READY,
                        DeliveryTask.Status.ASSIGNED,
                    ):
                        return False
            return True
        return True
    if not profile:
        return False
    if profile.role == "observer":
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


class DeliverySettingsView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        row, _ = DeliverySettings.objects.get_or_create(
            workspace=self.get_workspace()
        )
        return Response(DeliverySettingsSerializer(row).data)

    def patch(self, request):
        self.require_editor()
        row, _ = DeliverySettings.objects.get_or_create(
            workspace=self.get_workspace()
        )
        if "agent_ops_enabled" in request.data:
            row.agent_ops_enabled = bool(request.data.get("agent_ops_enabled"))
            row.save(update_fields=["agent_ops_enabled", "updated_at"])
        return Response(DeliverySettingsSerializer(row).data)


class ProjectMetaListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        rows = DeliveryProjectMeta.objects.filter(workspace=ws).select_related("project")
        return Response(DeliveryProjectMetaSerializer(rows, many=True).data)

    def post(self, request):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        project_id = request.data.get("project")
        if not project_id:
            raise ValidationError({"project": "Required"})
        row, _ = DeliveryProjectMeta.objects.update_or_create(
            workspace=ws,
            project_id=project_id,
            defaults={
                "repo_url": request.data.get("repo_url") or "",
                "docs_url": request.data.get("docs_url") or "",
            },
        )
        return Response(DeliveryProjectMetaSerializer(row).data, status=201)


class AgentProfileListCreateView(WorkspaceMixin, APIView):
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


class AgentServiceAccountCreateView(WorkspaceMixin, APIView):
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


class AgentActionLogListView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        rows = AgentActionLog.objects.filter(workspace=ws)[:200]
        return Response(AgentActionLogSerializer(rows, many=True).data)


class AccessLogListView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        self.require_editor()
        rows = DeliveryAccessLog.objects.filter(workspace=ws)[:200]
        return Response(DeliveryAccessLogSerializer(rows, many=True).data)


class EpicListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        _log_access(ws, request, 200)
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
        _log_access(ws, request, 201)
        return Response(EpicSerializer(row).data, status=201)


class EpicDetailView(WorkspaceMixin, APIView):
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


class SprintListCreateView(WorkspaceMixin, APIView):
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


class SprintDetailView(WorkspaceMixin, APIView):
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


class TaskListCreateView(WorkspaceMixin, APIView):
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
        _log_access(ws, request, 200)
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
        _log_access(ws, request, 201)
        return resp


class TaskDetailView(WorkspaceMixin, APIView):
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
        if (
            profile
            and profile.actor_type == AgentProfile.ActorType.AGENT
            and profile.role not in ("owner", "planner", "documentation")
        ):
            touched = MEANING_FIELDS.intersection(request.data.keys())
            if touched and not request.data.get("confirm_meaning_change"):
                raise PermissionDenied(
                    "Agents cannot change task meaning without confirm_meaning_change."
                )
        before = snapshot_task(task)
        ser = DeliveryTaskWriteSerializer(task, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        for k, v in ser.validated_data.items():
            setattr(task, k, v)
        task.version += 1
        task.save()
        record_field_changes(
            task, user=request.user, before=before, after=snapshot_task(task)
        )
        return Response(DeliveryTaskSerializer(task).data)


class TaskStatusView(WorkspaceMixin, APIView):
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


class TaskClaimView(WorkspaceMixin, APIView):
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


class TaskHistoryView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, task_id):
        ws = self.get_workspace()
        _ensure_ops_enabled(ws)
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        status_rows = TaskStatusHistory.objects.filter(task=task)
        field_rows = TaskFieldHistory.objects.filter(task=task)[:200]
        return Response(
            {
                "status_history": StatusHistorySerializer(status_rows, many=True).data,
                "field_history": FieldHistorySerializer(field_rows, many=True).data,
            }
        )


class TaskBlockerListCreateView(WorkspaceMixin, APIView):
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


class TaskBlockerResolveView(WorkspaceMixin, APIView):
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


class TaskBlockerCancelView(WorkspaceMixin, APIView):
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


class TaskHandoffCreateView(WorkspaceMixin, APIView):
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


class TaskCommentListCreateView(WorkspaceMixin, APIView):
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
        task = get_object_or_404(DeliveryTask.objects.filter(workspace=ws), pk=task_id)
        body = (request.data.get("body") or "").strip()
        if not body:
            raise ValidationError({"body": "Required"})
        kind = request.data.get("kind") or TaskComment.Kind.COMMENT
        row = TaskComment.objects.create(
            task=task, body=body, kind=kind, author=request.user
        )
        return Response(CommentSerializer(row).data, status=201)


class TaskSubTaskListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

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
        )
        return Response(SubTaskSerializer(row).data, status=201)


class TaskDependencyListCreateView(WorkspaceMixin, APIView):
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
        other = get_object_or_404(
            DeliveryTask.objects.filter(workspace=ws), pk=depends_on_id
        )
        dep, created = TaskDependency.objects.get_or_create(
            task=task, depends_on=other
        )
        return Response(
            DependencySerializer(dep).data, status=201 if created else 200
        )


class TaskPrSnippetView(WorkspaceMixin, APIView):
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


class AgentQueueView(WorkspaceMixin, APIView):
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
        updated = 0
        for task in DeliveryTask.objects.filter(
            github_repo=full_name, github_pr_number=number
        ):
            if pr:
                task.github_pr_state = state or task.github_pr_state
                task.github_pr_url = html_url or task.github_pr_url
                if head:
                    task.github_branch = head
                if sha:
                    task.github_commit = sha[:64]
                if action in ("synchronize", "opened", "reopened", "closed"):
                    task.github_checks_status = state
            notes = []
            if review.get("body"):
                notes.append(
                    f"[{review.get('state', 'review')}] {review.get('body')}"
                )
            if comment.get("body") and event in (
                "pull_request_review_comment",
                "issue_comment",
                "",
            ):
                notes.append(comment.get("body"))
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


class OverviewView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
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
        awaiting = TaskBlocker.objects.filter(
            task__workspace=ws,
            needs_owner_decision=True,
            resolved_at__isnull=True,
            cancelled_at__isnull=True,
        ).select_related("task")[:50]
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
                "awaiting_owner": [
                    {
                        "blocker_id": b.id,
                        "title": b.title,
                        "task_id": b.task_id,
                        "task_title": b.task.title,
                    }
                    for b in awaiting
                ],
                "returned_from_qa": DeliveryTaskSerializer(returned, many=True).data,
            }
        )
