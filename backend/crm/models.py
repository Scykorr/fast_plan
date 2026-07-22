from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


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
    job_title = models.CharField(max_length=120, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    birth_date = models.DateField(null=True, blank=True)
    remind_before_days = models.PositiveSmallIntegerField(default=7)
    # Optional back-links to legacy models after sync.
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

    def __str__(self):
        return self.subject
