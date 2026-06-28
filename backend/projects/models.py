from django.conf import settings
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
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

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
