"""P9 Agent Ops: epics, sprints, delivery tasks, handoffs, agent roles (TZ-complete)."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class DeliverySettings(models.Model):
    """Per-workspace feature flag for Agent Ops UI/API."""

    workspace = models.OneToOneField(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="delivery_settings",
    )
    agent_ops_enabled = models.BooleanField(default=False)
    github_webhook_secret = models.CharField(max_length=255, blank=True, default="")
    # Optional PAT for attaching task links to PRs (TZ §10 desirable)
    github_api_token = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"delivery settings ws={self.workspace_id}"


class AgentRole(models.TextChoices):
    OWNER = "owner", "Owner"
    DOCUMENTATION = "documentation", "Documentation Agent"
    SMART_CONTRACT = "smart_contract", "Smart Contract Agent"
    BACKEND = "backend", "Backend Agent"
    FRONTEND = "frontend", "Frontend Agent"
    QA = "qa", "QA Agent"
    HUMAN = "human", "Human Contributor"
    OBSERVER = "observer", "Observer"
    PLANNER = "planner", "Planner"
    REVIEWER = "reviewer", "Reviewer"


# TZ §4 / §12 — default action sets per role
ROLE_DEFAULT_ACTIONS: dict[str, list[str]] = {
    AgentRole.PLANNER: [
        "read",
        "write_task",
        "write_epic",
        "write_sprint",
        "comment",
        "assign",
        "claim",
        "handoff",
        "blocker",
    ],
    AgentRole.OWNER: [
        "read",
        "write_task",
        "write_epic",
        "write_sprint",
        "claim",
        "handoff",
        "comment",
        "blocker",
        "close_epic",
        "assign",
        "manage_agents",
        "review",
    ],
    AgentRole.DOCUMENTATION: [
        "read",
        "write_task",
        "handoff",
        "comment",
        "blocker",
        "claim",
    ],
    AgentRole.SMART_CONTRACT: [
        "read",
        "claim",
        "write_task_own",
        "handoff",
        "comment",
        "blocker",
    ],
    AgentRole.BACKEND: [
        "read",
        "claim",
        "write_task_own",
        "handoff",
        "comment",
        "blocker",
    ],
    AgentRole.FRONTEND: [
        "read",
        "claim",
        "write_task_own",
        "handoff",
        "comment",
        "blocker",
    ],
    AgentRole.QA: [
        "read",
        "claim",
        "write_task_own",
        "handoff",
        "comment",
        "blocker",
        "review",
    ],
    AgentRole.REVIEWER: [
        "read",
        "comment",
        "review",
        "blocker",
    ],
    AgentRole.HUMAN: [
        "read",
        "claim",
        "write_task_own",
        "handoff",
        "comment",
        "blocker",
    ],
    AgentRole.OBSERVER: ["read"],
}


class DeliveryProjectMeta(models.Model):
    """TZ §5.1 delivery links on an existing Project (repo + docs)."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="delivery_project_meta",
    )
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="delivery_meta",
    )
    repo_url = models.URLField(blank=True, default="")
    docs_url = models.URLField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"delivery meta project={self.project_id}"


class AgentProfile(models.Model):
    """Maps a workspace user (or service account) to an agent/human delivery role."""

    class ActorType(models.TextChoices):
        HUMAN = "human", "Human"
        AGENT = "agent", "Agent"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="delivery_agent_profiles",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delivery_agent_profiles",
    )
    role = models.CharField(max_length=32, choices=AgentRole.choices)
    actor_type = models.CharField(
        max_length=16, choices=ActorType.choices, default=ActorType.HUMAN
    )
    display_name = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_service_account = models.BooleanField(default=False)
    # Empty list → use ROLE_DEFAULT_ACTIONS[role]
    allowed_actions = models.JSONField(default=list, blank=True)
    # Empty M2M → all projects in workspace
    allowed_projects = models.ManyToManyField(
        "projects.Project",
        blank=True,
        related_name="delivery_agent_profiles",
    )
    api_token = models.ForeignKey(
        "workspaces.WorkspaceAPIToken",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_agent_profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["role", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user"],
                name="uniq_delivery_agent_profile_ws_user",
            )
        ]

    def effective_actions(self) -> list[str]:
        if self.allowed_actions:
            return list(self.allowed_actions)
        return list(ROLE_DEFAULT_ACTIONS.get(self.role, ["read"]))

    def can(self, action: str) -> bool:
        actions = self.effective_actions()
        return action in actions or "write_task" in actions and action == "write_task_own"

    def __str__(self):
        return f"{self.role} ({self.user_id}) @ {self.workspace_id}"


class AgentActionLog(models.Model):
    """TZ §4 — journal of agent-profile actions."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="delivery_agent_action_logs",
    )
    profile = models.ForeignKey(
        AgentProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="action_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=64, blank=True, default="")
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    detail = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Epic(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        ARCHIVED = "archived", "Archived"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="delivery_epics",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_epics",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    goal = models.TextField(blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_delivery_epics",
    )
    priority = models.CharField(
        max_length=16, choices=Priority.choices, default=Priority.NORMAL
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    planning_doc_url = models.URLField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.title


class Sprint(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="delivery_sprints",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_sprints",
    )
    name = models.CharField(max_length=255)
    goal = models.TextField(blank=True, default="")
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PLANNED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_on", "-id"]

    def __str__(self):
        return self.name


class DeliveryTask(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        READY = "ready", "Готово к назначению"
        ASSIGNED = "assigned", "Назначено"
        IN_PROGRESS = "in_progress", "В работе"
        BLOCKED = "blocked", "Заблокировано"
        REVIEW = "review", "На проверке"
        QA = "qa", "На проверке"
        NEEDS_REWORK = "needs_rework", "Нужна доработка"
        READY_FOR_OWNER = "ready_for_owner", "Готово к решению владельца"
        DONE = "done", "Завершено"
        ARCHIVED = "archived", "Архив"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class TaskType(models.TextChoices):
        FEATURE = "feature", "Feature"
        BUG = "bug", "Bug"
        DOCS = "docs", "Docs"
        INFRA = "infra", "Infra"
        RESEARCH = "research", "Research"
        OTHER = "other", "Other"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="delivery_tasks",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_tasks",
    )
    epic = models.ForeignKey(
        Epic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    sprint = models.ForeignKey(
        Sprint,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    business_outcome = models.TextField(blank=True, default="")
    context = models.TextField(blank=True, default="")
    task_type = models.CharField(
        max_length=20, choices=TaskType.choices, default=TaskType.FEATURE
    )
    priority = models.CharField(
        max_length=16, choices=Priority.choices, default=Priority.NORMAL
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    assignee_role = models.CharField(
        max_length=32, choices=AgentRole.choices, blank=True, default=""
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_delivery_tasks",
    )
    previous_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="previously_assigned_delivery_tasks",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_delivery_tasks",
    )
    ready_criterion = models.TextField(blank=True, default="")
    done_criterion = models.TextField(blank=True, default="")
    scope_in = models.TextField(blank=True, default="")
    scope_out = models.TextField(blank=True, default="")
    expected_checks = models.TextField(blank=True, default="")
    result_artifact = models.TextField(blank=True, default="")
    implementation_summary = models.TextField(blank=True, default="")
    expected_next_step = models.TextField(blank=True, default="")
    next_role = models.CharField(
        max_length=32, choices=AgentRole.choices, blank=True, default=""
    )
    canon_url = models.URLField(blank=True, default="")
    architecture_url = models.URLField(blank=True, default="")
    planning_doc_url = models.URLField(blank=True, default="")
    acceptance_url = models.URLField(blank=True, default="")
    external_pack_url = models.URLField(blank=True, default="")
    github_repo = models.CharField(max_length=255, blank=True, default="")
    github_branch = models.CharField(max_length=255, blank=True, default="")
    github_commit = models.CharField(max_length=64, blank=True, default="")
    github_commits = models.JSONField(default=list, blank=True)
    github_pr_url = models.URLField(blank=True, default="")
    github_pr_number = models.PositiveIntegerField(null=True, blank=True)
    github_pr_state = models.CharField(max_length=32, blank=True, default="")
    github_checks_url = models.URLField(blank=True, default="")
    github_checks_status = models.CharField(max_length=32, blank=True, default="")
    github_review_notes = models.TextField(blank=True, default="")
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["workspace", "assignee_role", "status"]),
            models.Index(fields=["workspace", "sprint", "status"]),
        ]

    def __str__(self):
        return self.title


class TaskDependency(models.Model):
    """TZ §5.4 — task depends on another task in the same workspace."""

    task = models.ForeignKey(
        DeliveryTask, on_delete=models.CASCADE, related_name="dependencies"
    )
    depends_on = models.ForeignKey(
        DeliveryTask, on_delete=models.CASCADE, related_name="dependents"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["task", "depends_on"],
                name="uniq_delivery_task_dependency",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.task_id and self.depends_on_id and self.task_id == self.depends_on_id:
            raise ValidationError("Task cannot depend on itself.")


class DeliverySubTask(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        DOING = "doing", "Doing"
        DONE = "done", "Done"

    task = models.ForeignKey(
        DeliveryTask, on_delete=models.CASCADE, related_name="subtasks"
    )
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.TODO
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_subtasks",
    )
    expected_artifact = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class TaskStatusHistory(models.Model):
    task = models.ForeignKey(
        DeliveryTask, on_delete=models.CASCADE, related_name="status_history"
    )
    from_status = models.CharField(max_length=20, blank=True, default="")
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class TaskFieldHistory(models.Model):
    """TZ §13 — field-level change journal."""

    task = models.ForeignKey(
        DeliveryTask, on_delete=models.CASCADE, related_name="field_history"
    )
    field = models.CharField(max_length=64)
    old_value = models.TextField(blank=True, default="")
    new_value = models.TextField(blank=True, default="")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class TaskBlocker(models.Model):
    task = models.ForeignKey(
        DeliveryTask, on_delete=models.CASCADE, related_name="blockers"
    )
    title = models.CharField(max_length=255)
    detail = models.TextField(blank=True, default="")
    needs_owner_decision = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_delivery_blockers",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_delivery_blockers",
    )
    resolution_note = models.TextField(blank=True, default="")
    # Soft-cancel with trail (TZ §12 — no silent delete)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_delivery_blockers",
    )
    cancel_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None and self.cancelled_at is None


class TaskHandoff(models.Model):
    task = models.ForeignKey(
        DeliveryTask, on_delete=models.CASCADE, related_name="handoffs"
    )
    from_role = models.CharField(max_length=32, choices=AgentRole.choices)
    to_role = models.CharField(max_length=32, choices=AgentRole.choices)
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_handoffs_sent",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_handoffs_received",
    )
    reason = models.TextField(blank=True, default="")
    expected_next_step = models.TextField(blank=True, default="")
    done_summary = models.TextField()
    left_summary = models.TextField(blank=True, default="")
    branch_or_pr_url = models.URLField(blank=True, default="")
    checks_url = models.URLField(blank=True, default="")
    open_questions = models.TextField(blank=True, default="")
    needs_owner_decision = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class TaskComment(models.Model):
    class Kind(models.TextChoices):
        COMMENT = "comment", "Рабочий комментарий"
        RESULT = "result", "Результат выполнения"
        HANDOFF_NOTE = "handoff_note", "Передача следующему исполнителю"
        REVIEW_FINDING = "review_finding", "Замечание проверки"
        BLOCKER_NOTE = "blocker_note", "Блокер"
        OWNER_REQUEST = "owner_request", "Запрос решения владельца"
        OWNER_DECISION = "owner_decision", "Решение владельца"

    task = models.ForeignKey(
        DeliveryTask, on_delete=models.CASCADE, related_name="comments"
    )
    kind = models.CharField(
        max_length=20, choices=Kind.choices, default=Kind.COMMENT
    )
    body = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class DeliveryIdempotencyKey(models.Model):
    """Stores responses for Idempotency-Key on mutating agent API calls."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="delivery_idempotency_keys",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delivery_idempotency_keys",
    )
    key = models.CharField(max_length=128)
    method = models.CharField(max_length=16)
    path = models.CharField(max_length=255)
    status_code = models.PositiveIntegerField()
    response_body = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user", "key"],
                name="uniq_delivery_idempotency_ws_user_key",
            )
        ]
        indexes = [models.Index(fields=["created_at"])]


class DeliveryAccessLog(models.Model):
    """TZ §9.1 — journal of delivery API requests."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="delivery_access_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    method = models.CharField(max_length=16)
    path = models.CharField(max_length=255)
    status_code = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["workspace", "created_at"])]


class TaskMeaningChangeRequest(models.Model):
    """TZ §12 — agents propose meaning changes; Owner/Planner must approve."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    task = models.ForeignKey(
        DeliveryTask, on_delete=models.CASCADE, related_name="meaning_change_requests"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_meaning_requests",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_meaning_reviews",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    proposed_fields = models.JSONField(default=dict)
    note = models.TextField(blank=True, default="")
    review_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class TaskGitHubReview(models.Model):
    """TZ §10 — structured open review remarks (not a blob)."""

    class State(models.TextChoices):
        COMMENTED = "commented", "Commented"
        APPROVED = "approved", "Approved"
        CHANGES_REQUESTED = "changes_requested", "Changes requested"
        DISMISSED = "dismissed", "Dismissed"
        OPEN = "open", "Open"

    task = models.ForeignKey(
        DeliveryTask, on_delete=models.CASCADE, related_name="github_reviews"
    )
    github_link = models.ForeignKey(
        "TaskGitHubLink",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )
    github_review_id = models.BigIntegerField(null=True, blank=True)
    author_login = models.CharField(max_length=255, blank=True, default="")
    state = models.CharField(max_length=32, choices=State.choices, default=State.OPEN)
    body = models.TextField(blank=True, default="")
    html_url = models.URLField(blank=True, default="")
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["task", "is_resolved"])]


class TaskGitHubLink(models.Model):
    """TZ §10 — multiple PR/branch links per task (primary synced to task fields)."""

    task = models.ForeignKey(
        DeliveryTask, on_delete=models.CASCADE, related_name="github_links"
    )
    repo = models.CharField(max_length=255, blank=True, default="")
    branch = models.CharField(max_length=255, blank=True, default="")
    commit = models.CharField(max_length=64, blank=True, default="")
    pr_number = models.PositiveIntegerField(null=True, blank=True)
    pr_url = models.URLField(blank=True, default="")
    pr_state = models.CharField(max_length=32, blank=True, default="")
    checks_url = models.URLField(blank=True, default="")
    checks_status = models.CharField(max_length=32, blank=True, default="")
    is_primary = models.BooleanField(default=False)
    attached_to_pr = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "-updated_at", "-id"]
        indexes = [
            models.Index(fields=["repo", "pr_number"]),
            models.Index(fields=["repo", "branch"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["task", "repo", "pr_number"],
                name="uniq_delivery_task_github_pr",
                condition=models.Q(pr_number__isnull=False),
            )
        ]

    def __str__(self):
        return f"{self.repo}#{self.pr_number or self.branch}"
