"""Process domain models: BPMN definitions, instances, user tasks, DMN, CMMN."""

from django.conf import settings
from django.db import models


class ProcessDefinition(models.Model):
    """Editable BPMN process definition (workspace-scoped)."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="process_definitions",
    )
    key = models.SlugField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    bpmn_xml = models.TextField()
    process_id = models.CharField(
        max_length=100,
        help_text="BPMN process@id used by SpiffWorkflow",
    )
    version = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=False)
    category = models.CharField(max_length=64, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_process_definitions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "key"]
        unique_together = [("workspace", "key", "version")]

    def __str__(self):
        return f"{self.key}@v{self.version} ({self.name})"


class ProcessDeployment(models.Model):
    """Immutable snapshot of a published definition used for execution."""

    definition = models.ForeignKey(
        ProcessDefinition,
        on_delete=models.CASCADE,
        related_name="deployments",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="process_deployments",
    )
    version = models.PositiveIntegerField()
    bpmn_xml = models.TextField()
    process_id = models.CharField(max_length=100)
    deployed_at = models.DateTimeField(auto_now_add=True)
    deployed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-deployed_at"]
        unique_together = [("definition", "version")]

    def __str__(self):
        return f"deploy {self.definition.key}@v{self.version}"


class ProcessInstance(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ERROR = "error", "Error"
        CANCELLED = "cancelled", "Cancelled"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="process_instances",
    )
    deployment = models.ForeignKey(
        ProcessDeployment,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    business_key = models.CharField(max_length=255, blank=True, default="")
    deal = models.ForeignKey(
        "crm.Deal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="process_instances",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="process_instances",
    )
    organization = models.ForeignKey(
        "crm.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="process_instances",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    data = models.JSONField(default=dict, blank=True)
    state_json = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="started_process_instances",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"instance {self.id} {self.status}"


class ActivityInstance(models.Model):
    class Status(models.TextChoices):
        READY = "ready", "Ready"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ERROR = "error", "Error"

    instance = models.ForeignKey(
        ProcessInstance,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    task_id = models.CharField(max_length=120)
    task_name = models.CharField(max_length=255, blank=True, default="")
    task_type = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.READY
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class UserTask(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="process_user_tasks",
    )
    instance = models.ForeignKey(
        ProcessInstance,
        on_delete=models.CASCADE,
        related_name="user_tasks",
    )
    activity = models.OneToOneField(
        ActivityInstance,
        on_delete=models.CASCADE,
        related_name="user_task",
        null=True,
        blank=True,
    )
    spiff_task_id = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_process_tasks",
    )
    candidate_role = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="workspace role or crm_role candidate group",
    )
    form_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON Schema-like form for P8c",
    )
    form_data = models.JSONField(default=dict, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_process_tasks",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"task {self.name} ({self.status})"


class DecisionDefinition(models.Model):
    """DMN decision table (P8b)."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="decision_definitions",
    )
    key = models.SlugField(max_length=100)
    name = models.CharField(max_length=255)
    dmn_xml = models.TextField()
    decision_id = models.CharField(max_length=100)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("workspace", "key", "version")]


class CaseDefinition(models.Model):
    """CMMN-lite case definition (P8d) — stages as JSON plan items."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="case_definitions",
    )
    key = models.SlugField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    # stages: [{id, name, discretionary, required?, depends_on?, process_key?}]
    plan_items = models.JSONField(default=list, blank=True)
    cmmn_xml = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("workspace", "key")]


class CaseInstance(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="case_instances",
    )
    definition = models.ForeignKey(
        CaseDefinition,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    deal = models.ForeignKey(
        "crm.Deal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="case_instances",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="case_instances",
    )
    # completed plan item ids
    completed_items = models.JSONField(default=list, blank=True)
    data = models.JSONField(default=dict, blank=True)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]


class ProcessTimer(models.Model):
    """Deferred timer continuation for BPMN timer events."""

    instance = models.ForeignKey(
        ProcessInstance,
        on_delete=models.CASCADE,
        related_name="timers",
    )
    spiff_task_id = models.CharField(max_length=120)
    fire_at = models.DateTimeField()
    fired = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fire_at"]
