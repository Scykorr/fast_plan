"""Project-scoped Scrum (Scrum Guide MVP): Product Backlog + Sprints + SP burndown."""

from django.conf import settings
from django.db import models


class ScrumSprint(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="scrum_sprints",
    )
    name = models.CharField(max_length=255)
    goal = models.TextField(blank=True, default="")
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_on", "-id"]

    def __str__(self):
        return f"{self.project_id}:{self.name}"


class ProductBacklogItem(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="scrum_pbis",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    story_points = models.PositiveSmallIntegerField(null=True, blank=True)
    priority = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    sprint = models.ForeignKey(
        ScrumSprint,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pbis",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrum_pbis",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_scrum_pbis",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rank", "id"]
        indexes = [
            models.Index(fields=["project", "sprint", "status"]),
        ]

    def __str__(self):
        return self.title
