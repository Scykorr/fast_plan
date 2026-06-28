from django.db import models

from workspaces.models import Workspace


class Board(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="boards",
    )
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="board",
    )
    title = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at"]

    def __str__(self):
        return self.title


class Column(models.Model):
    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name="columns",
    )
    title = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.title


class Card(models.Model):
    column = models.ForeignKey(
        Column,
        on_delete=models.CASCADE,
        related_name="cards",
    )
    wbs_node = models.OneToOneField(
        "projects.WBSNode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="card",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.title
