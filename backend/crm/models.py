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


class Pipeline(models.Model):
    """Sales pipeline for a workspace (one default board of stages)."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_pipelines",
    )
    name = models.CharField(max_length=120, default="Продажи")
    is_default = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class PipelineStage(models.Model):
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name="stages",
    )
    name = models.CharField(max_length=120)
    position = models.PositiveIntegerField(default=0)
    default_probability = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["pipeline", "name"],
                name="uniq_crm_pipeline_stage_name",
            ),
        ]

    def __str__(self):
        return self.name


class Deal(models.Model):
    """Sales opportunity in a pipeline stage."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_deals",
    )
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name="deals",
    )
    stage = models.ForeignKey(
        PipelineStage,
        on_delete=models.PROTECT,
        related_name="deals",
    )
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    probability = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    close_date = models.DateField(null=True, blank=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_deals",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_crm_deals",
    )
    position = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["stage__position", "position", "id"]
        indexes = [
            models.Index(fields=["workspace", "stage"]),
            models.Index(fields=["workspace", "close_date"]),
        ]

    def __str__(self):
        return self.title

    @property
    def weighted_amount(self):
        return (self.amount * self.probability) / 100

    @property
    def is_open(self):
        return not self.stage.is_won and not self.stage.is_lost


class DealTask(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    due_date = models.DateField(null=True, blank=True)
    is_done = models.BooleanField(default=False)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_deal_tasks",
    )
    remind_before_days = models.PositiveSmallIntegerField(default=1)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["is_done", "due_date", "id"]

    def __str__(self):
        return self.title


class Lead(models.Model):
    """Inbound / sales lead before qualification into a Deal."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        DISQUALIFIED = "disqualified", "Disqualified"
        CONVERTED = "converted", "Converted"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_leads",
    )
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=64, blank=True, default="")
    company_name = models.CharField(max_length=255, blank=True, default="")
    source = models.CharField(max_length=120, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW
    )
    score = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_crm_leads",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    deal = models.ForeignKey(
        "Deal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_leads",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-score", "-created_at", "-id"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["workspace", "email"]),
            models.Index(fields=["workspace", "phone"]),
        ]

    def __str__(self):
        return self.full_name


class LeadAssignmentState(models.Model):
    """Round-robin cursor for lead assignment per workspace."""

    workspace = models.OneToOneField(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_lead_assignment",
    )
    last_user_id = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class AutomationRule(models.Model):
    """Declarative CRM automation: trigger → conditions → actions."""

    class Trigger(models.TextChoices):
        LEAD_CREATED = "lead.created", "Lead created"
        LEAD_CONVERTED = "lead.converted", "Lead converted"
        DEAL_CREATED = "deal.created", "Deal created"
        DEAL_STAGE_CHANGED = "deal.stage_changed", "Deal stage changed"
        SCHEDULE_DAILY = "schedule.daily", "Daily schedule"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_automations",
    )
    name = models.CharField(max_length=160)
    is_active = models.BooleanField(default=True)
    trigger = models.CharField(max_length=40, choices=Trigger.choices)
    # [{"field": "source", "op": "eq|neq|contains|gte|lte|in", "value": ...}]
    conditions = models.JSONField(default=list, blank=True)
    # [{"type": "assign_round_robin|create_deal_task|create_deal|create_lead|assign|webhook|delay|set_status", ...}]
    actions = models.JSONField(default=list, blank=True)
    template_key = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class AutomationRun(models.Model):
    rule = models.ForeignKey(
        AutomationRule, on_delete=models.CASCADE, related_name="runs"
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_automation_runs",
    )
    trigger = models.CharField(max_length=40)
    context = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class AutomationDeferred(models.Model):
    """Delayed remaining actions from a rule run."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="crm_automation_deferred",
    )
    rule = models.ForeignKey(
        AutomationRule,
        on_delete=models.CASCADE,
        related_name="deferred",
        null=True,
        blank=True,
    )
    actions = models.JSONField(default=list)
    context = models.JSONField(default=dict, blank=True)
    run_at = models.DateTimeField()
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["run_at", "id"]
        indexes = [
            models.Index(fields=["workspace", "run_at", "processed_at"]),
        ]
