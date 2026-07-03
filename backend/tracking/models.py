from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Tracker(models.Model):
    class Target(models.TextChoices):
        PROJECT = "project", "Project"
        ISSUE = "issue", "Issue"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="trackers",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    target = models.CharField(max_length=20, choices=Target.choices, default=Target.ISSUE)
    position = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "id"]
        unique_together = [("workspace", "name")]

    def __str__(self):
        return self.name


class IssueStatus(models.Model):
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="issue_statuses",
    )
    name = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    is_closed = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "id"]
        verbose_name_plural = "issue statuses"
        unique_together = [("workspace", "name")]

    def __str__(self):
        return self.name


class CustomField(models.Model):
    class FieldFormat(models.TextChoices):
        STRING = "string", "String"
        TEXT = "text", "Text"
        INT = "int", "Integer"
        FLOAT = "float", "Float"
        PERCENT = "percent", "Percent"
        BOOL = "bool", "Boolean"
        DATE = "date", "Date"
        DATETIME = "datetime", "DateTime"
        LIST = "list", "List"
        LINK_LIST = "link_list", "Link list"
        USER = "user", "User"
        URL = "url", "URL"
        EMAIL = "email", "Email"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="custom_fields",
    )
    name = models.CharField(max_length=255)
    field_format = models.CharField(max_length=20, choices=FieldFormat.choices)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    default_value = models.TextField(blank=True)
    trackers = models.ManyToManyField(
        Tracker,
        through="CustomFieldTracker",
        related_name="custom_fields",
        blank=True,
    )

    class Meta:
        ordering = ["position", "id"]
        unique_together = [("workspace", "name")]

    def __str__(self):
        return self.name


class CustomFieldTracker(models.Model):
    custom_field = models.ForeignKey(
        CustomField,
        on_delete=models.CASCADE,
        related_name="tracker_links",
    )
    tracker = models.ForeignKey(
        Tracker,
        on_delete=models.CASCADE,
        related_name="field_links",
    )

    class Meta:
        unique_together = [("custom_field", "tracker")]


class CustomFieldEnumeration(models.Model):
    custom_field = models.ForeignKey(
        CustomField,
        on_delete=models.CASCADE,
        related_name="enumerations",
    )
    name = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    class Meta:
        ordering = ["position", "id"]
        unique_together = [("custom_field", "parent", "name")]

    def __str__(self):
        return self.name


class CustomValue(models.Model):
    custom_field = models.ForeignKey(
        CustomField,
        on_delete=models.CASCADE,
        related_name="values",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    value = models.TextField(blank=True)

    class Meta:
        unique_together = [("custom_field", "content_type", "object_id")]

    def __str__(self):
        return f"{self.custom_field.name}={self.value}"
