from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Organization(models.Model):
    """B2B account / company in a workspace directory."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_organizations",
    )
    name = models.CharField(max_length=255)
    website = models.URLField(blank=True, default="")
    industry = models.CharField(max_length=120, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_crm_organizations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="uniq_crm_org_workspace_name",
            ),
        ]

    def __str__(self):
        return self.name


class Person(models.Model):
    """Workspace-scoped person in the CRM directory."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_people",
    )
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=64, blank=True, default="")
    telegram = models.CharField(max_length=120, blank=True, default="")
    whatsapp = models.CharField(max_length=64, blank=True, default="")
    social_urls = models.JSONField(default=list, blank=True)
    job_title = models.CharField(max_length=120, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    birth_date = models.DateField(null=True, blank=True)
    remind_before_days = models.PositiveSmallIntegerField(default=7)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_crm_people",
    )
    legacy_contact = models.OneToOneField(
        "birthdays.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_person",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_person_profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name", "id"]
        indexes = [
            models.Index(fields=["workspace", "email"]),
            models.Index(fields=["workspace", "full_name"]),
        ]

    def __str__(self):
        return self.full_name


class OrganizationMembership(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    title = models.CharField(max_length=120, blank=True, default="")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "person"],
                name="uniq_crm_org_person",
            ),
        ]

    def __str__(self):
        return f"{self.person_id} @ {self.organization_id}"


class Tag(models.Model):
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_tags",
    )
    name = models.CharField(max_length=64)
    color = models.CharField(max_length=16, blank=True, default="#3b82f6")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="uniq_crm_tag_workspace_name",
            ),
        ]

    def __str__(self):
        return self.name


class PersonTag(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="tag_links")
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="person_links")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["person", "tag"], name="uniq_crm_person_tag"),
        ]


class OrganizationTag(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="tag_links"
    )
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="organization_links")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "tag"], name="uniq_crm_org_tag"
            ),
        ]


class Segment(models.Model):
    """Manual or rule-based list of people/orgs."""

    class Kind(models.TextChoices):
        MANUAL = "manual", "Manual"
        RULE = "rule", "Rule"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_segments",
    )
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.MANUAL)
    # Example rule: {"stale_days": 14, "tag": "vip"} — evaluated in services.
    rule = models.JSONField(default=dict, blank=True)
    people = models.ManyToManyField(Person, blank=True, related_name="segments")
    organizations = models.ManyToManyField(
        Organization, blank=True, related_name="segments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="uniq_crm_segment_workspace_name",
            ),
        ]

    def __str__(self):
        return self.name


class CrmComment(models.Model):
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_comments",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_comments",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(person__isnull=False, organization__isnull=True)
                    | Q(person__isnull=True, organization__isnull=False)
                ),
                name="crm_comment_exactly_one_target",
            ),
        ]


def crm_file_upload_path(instance, filename):
    if instance.person_id:
        return f"crm/people/{instance.person_id}/{filename}"
    return f"crm/orgs/{instance.organization_id}/{filename}"


class CrmAttachment(models.Model):
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_attachments",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
    )
    file = models.FileField(upload_to=crm_file_upload_path)
    name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=150, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_uploaded_files",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(person__isnull=False, organization__isnull=True)
                    | Q(person__isnull=True, organization__isnull=False)
                ),
                name="crm_attachment_exactly_one_target",
            ),
        ]


class ProjectPersonLink(models.Model):
    """Person role on a project (stakeholder-style engagement)."""

    class RoleKind(models.TextChoices):
        STAKEHOLDER = "stakeholder", "Stakeholder"
        SPONSOR = "sponsor", "Sponsor"
        CLIENT = "client", "Client contact"
        VENDOR = "vendor", "Vendor"
        OTHER = "other", "Other"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="crm_people",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="project_links",
    )
    role_kind = models.CharField(
        max_length=20,
        choices=RoleKind.choices,
        default=RoleKind.STAKEHOLDER,
    )
    role_label = models.CharField(max_length=255, blank=True, default="")
    interest = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    influence = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    notes = models.TextField(blank=True, default="")
    stakeholder = models.OneToOneField(
        "projects.Stakeholder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_link",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "person"],
                name="uniq_crm_project_person",
            ),
        ]

    def __str__(self):
        return f"{self.person_id} on project {self.project_id}"


class Activity(models.Model):
    class Kind(models.TextChoices):
        CALL = "call", "Call"
        MEETING = "meeting", "Meeting"
        EMAIL = "email", "Email"
        NOTE = "note", "Note"
        INVOICE = "invoice", "Invoice"
        ORDER = "order", "Order"
        OTHER = "other", "Other"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_activities",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.NOTE)
    subject = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    occurred_at = models.DateTimeField()
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_activities",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_activities_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["workspace", "occurred_at"]),
            models.Index(fields=["person", "occurred_at"]),
            models.Index(fields=["organization", "occurred_at"]),
        ]

    def __str__(self):
        return self.subject
