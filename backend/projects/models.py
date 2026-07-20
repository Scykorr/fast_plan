from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Project(models.Model):
    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_projects",
    )
    tracker = models.ForeignKey(
        "tracking.Tracker",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    workflow_status = models.ForeignKey(
        "tracking.IssueStatus",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ai_prompts = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ProjectTemplate(models.Model):
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="project_templates",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    structure = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_project_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]
        unique_together = [("workspace", "name")]

    def __str__(self):
        return self.name


class WBSNode(models.Model):
    class NodeType(models.TextChoices):
        DELIVERABLE = "deliverable", "Deliverable"
        WORK_PACKAGE = "work_package", "Work Package"
        MILESTONE = "milestone", "Milestone"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="wbs_nodes",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    code = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    node_type = models.CharField(
        max_length=20,
        choices=NodeType.choices,
        default=NodeType.DELIVERABLE,
    )
    position = models.PositiveIntegerField(default=0)
    tracker = models.ForeignKey(
        "tracking.Tracker",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wbs_nodes",
    )
    workflow_status = models.ForeignKey(
        "tracking.IssueStatus",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wbs_nodes",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_wbs_nodes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]
        unique_together = [("project", "code")]

    def __str__(self):
        return f"{self.code} {self.title}"


class ScheduleActivity(models.Model):
    wbs_node = models.OneToOneField(
        WBSNode,
        on_delete=models.CASCADE,
        related_name="schedule",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    duration_days = models.PositiveIntegerField(default=1)
    progress = models.PositiveSmallIntegerField(default=0)
    is_milestone = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "schedule activities"

    def __str__(self):
        return f"Schedule: {self.wbs_node.title}"


class ActivityDependency(models.Model):
    class DependencyType(models.TextChoices):
        FS = "FS", "Finish-Start"
        SS = "SS", "Start-Start"
        FF = "FF", "Finish-Finish"
        SF = "SF", "Start-Finish"

    predecessor = models.ForeignKey(
        ScheduleActivity,
        on_delete=models.CASCADE,
        related_name="successor_links",
    )
    successor = models.ForeignKey(
        ScheduleActivity,
        on_delete=models.CASCADE,
        related_name="predecessor_links",
    )
    dependency_type = models.CharField(
        max_length=2,
        choices=DependencyType.choices,
        default=DependencyType.FS,
    )
    lag_days = models.IntegerField(default=0)

    class Meta:
        unique_together = [("predecessor", "successor")]

    def __str__(self):
        return f"{self.predecessor} {self.dependency_type} {self.successor}"


class Risk(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MITIGATED = "mitigated", "Mitigated"
        CLOSED = "closed", "Closed"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="risks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    probability = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    impact = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    mitigation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-probability", "-impact", "id"]

    @property
    def score(self):
        return self.probability * self.impact

    def __str__(self):
        return self.title


class Stakeholder(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="stakeholders",
    )
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, blank=True)
    interest = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    influence = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    contact_email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class ProjectCharter(models.Model):
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="charter",
    )
    goals = models.TextField(blank=True)
    success_criteria = models.TextField(blank=True)
    constraints = models.TextField(blank=True)
    assumptions = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Charter: {self.project.name}"


class RACIEntry(models.Model):
    class RACIType(models.TextChoices):
        RESPONSIBLE = "R", "Responsible"
        ACCOUNTABLE = "A", "Accountable"
        CONSULTED = "C", "Consulted"
        INFORMED = "I", "Informed"

    wbs_node = models.ForeignKey(
        WBSNode,
        on_delete=models.CASCADE,
        related_name="raci_entries",
    )
    stakeholder = models.ForeignKey(
        Stakeholder,
        on_delete=models.CASCADE,
        related_name="raci_entries",
    )
    raci_type = models.CharField(max_length=1, choices=RACIType.choices)

    class Meta:
        unique_together = [("wbs_node", "stakeholder")]
        verbose_name_plural = "RACI entries"

    def __str__(self):
        return f"{self.wbs_node.code} — {self.stakeholder.name} ({self.raci_type})"


class ProjectBaseline(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="baselines",
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_baselines",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project.name} — {self.name}"


class BaselineActivity(models.Model):
    baseline = models.ForeignKey(
        ProjectBaseline,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    activity = models.ForeignKey(
        ScheduleActivity,
        on_delete=models.CASCADE,
        related_name="baseline_snapshots",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    duration_days = models.PositiveIntegerField(default=1)
    progress = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = [("baseline", "activity")]
        verbose_name_plural = "baseline activities"

    def __str__(self):
        return f"{self.baseline.name} — {self.activity}"


class WorkItemComment(models.Model):
    class Kind(models.TextChoices):
        COMMENT = "comment", "Comment"
        DECISION = "decision", "Decision"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="work_item_comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="work_item_comments",
    )
    wbs_node = models.ForeignKey(
        WBSNode,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",
    )
    card = models.ForeignKey(
        "kanban.Card",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",
    )
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.COMMENT,
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(wbs_node__isnull=False, card__isnull=True)
                    | models.Q(wbs_node__isnull=True, card__isnull=False)
                ),
                name="workitemcomment_exactly_one_target",
            )
        ]

    def __str__(self):
        return f"{self.kind}: {self.body[:40]}"


class ProjectShareLink(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="share_links",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    label = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_share_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_active(self):
        from django.utils import timezone

        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at <= timezone.now():
            return False
        return True


class ProjectMember(models.Model):
    class Role(models.TextChoices):
        MANAGER = "manager", "Manager"
        CONTRIBUTOR = "contributor", "Contributor"
        VIEWER = "viewer", "Viewer"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CONTRIBUTOR)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("project", "user")]
        ordering = ["role", "id"]

    def __str__(self):
        return f"{self.user} @ {self.project} ({self.role})"

