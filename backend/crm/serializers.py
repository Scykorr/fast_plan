from django.utils import timezone
from rest_framework import serializers

from crm.models import (
    Activity,
    AutomationRule,
    AutomationRun,
    CrmAttachment,
    CrmComment,
    Deal,
    DealTask,
    Lead,
    Organization,
    OrganizationMembership,
    OrganizationTag,
    Person,
    PersonTag,
    Pipeline,
    PipelineStage,
    ProjectPersonLink,
    Segment,
    Tag,
)
from crm.services import days_since_touch, get_or_create_tag
from projects.models import Project
from workspaces.models import WorkspaceMember


def _owner_in_workspace(workspace, owner_id):
    if owner_id is None:
        return None
    member = WorkspaceMember.objects.filter(
        workspace=workspace, user_id=owner_id
    ).first()
    if member is None:
        raise serializers.ValidationError({"owner_id": "User is not a workspace member."})
    return member.user


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "color", "created_at"]
        read_only_fields = ["id", "created_at"]


class TagWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["name", "color"]

    def create(self, validated_data):
        return Tag.objects.create(workspace=self.context["workspace"], **validated_data)


class OrganizationSerializer(serializers.ModelSerializer):
    people_count = serializers.IntegerField(read_only=True, required=False)
    projects_count = serializers.IntegerField(read_only=True, required=False)
    owner_id = serializers.IntegerField(read_only=True, allow_null=True)
    owner_email = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    last_activity_at = serializers.DateTimeField(read_only=True, required=False, allow_null=True)
    days_since_touch = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "website",
            "industry",
            "notes",
            "owner_id",
            "owner_email",
            "tags",
            "people_count",
            "projects_count",
            "last_activity_at",
            "days_since_touch",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_owner_email(self, obj):
        return obj.owner.email if obj.owner_id else None

    def get_tags(self, obj):
        links = getattr(obj, "_prefetched_tags", None)
        if links is None:
            links = obj.tag_links.select_related("tag")
        return TagSerializer([link.tag for link in links], many=True).data

    def get_days_since_touch(self, obj):
        last = getattr(obj, "last_activity_at", None)
        return days_since_touch(last)


class OrganizationWriteSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(required=False, allow_null=True)
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )

    class Meta:
        model = Organization
        fields = ["name", "website", "industry", "notes", "owner_id", "tag_ids"]

    def create(self, validated_data):
        owner_id = validated_data.pop("owner_id", None)
        tag_ids = validated_data.pop("tag_ids", None)
        workspace = self.context["workspace"]
        owner = _owner_in_workspace(workspace, owner_id) if "owner_id" in self.initial_data else None
        org = Organization.objects.create(workspace=workspace, owner=owner, **validated_data)
        if tag_ids is not None:
            self._sync_tags(org, tag_ids)
        return org

    def update(self, instance, validated_data):
        owner_id = validated_data.pop("owner_id", None)
        tag_ids = validated_data.pop("tag_ids", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if "owner_id" in self.initial_data:
            instance.owner = _owner_in_workspace(instance.workspace, owner_id)
        instance.save()
        if tag_ids is not None:
            self._sync_tags(instance, tag_ids)
        return instance

    def _sync_tags(self, org, tag_ids):
        workspace = org.workspace
        valid = set(
            Tag.objects.filter(workspace=workspace, id__in=tag_ids).values_list("id", flat=True)
        )
        OrganizationTag.objects.filter(organization=org).exclude(tag_id__in=valid).delete()
        existing = set(
            OrganizationTag.objects.filter(organization=org).values_list("tag_id", flat=True)
        )
        for tag_id in valid - existing:
            OrganizationTag.objects.create(organization=org, tag_id=tag_id)


class PersonSerializer(serializers.ModelSerializer):
    organizations = serializers.SerializerMethodField()
    projects_count = serializers.IntegerField(read_only=True, required=False)
    owner_id = serializers.IntegerField(read_only=True, allow_null=True)
    owner_email = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    last_activity_at = serializers.DateTimeField(read_only=True, required=False, allow_null=True)
    days_since_touch = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "telegram",
            "whatsapp",
            "social_urls",
            "job_title",
            "notes",
            "birth_date",
            "remind_before_days",
            "owner_id",
            "owner_email",
            "tags",
            "organizations",
            "projects_count",
            "last_activity_at",
            "days_since_touch",
            "legacy_contact_id",
            "user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_owner_email(self, obj):
        return obj.owner.email if obj.owner_id else None

    def get_tags(self, obj):
        links = getattr(obj, "_prefetched_tags", None)
        if links is None:
            links = obj.tag_links.select_related("tag")
        return TagSerializer([link.tag for link in links], many=True).data

    def get_days_since_touch(self, obj):
        last = getattr(obj, "last_activity_at", None)
        return days_since_touch(last)

    def get_organizations(self, obj):
        memberships = getattr(obj, "_prefetched_memberships", None)
        if memberships is None:
            memberships = obj.organization_memberships.select_related("organization")
        return [
            {
                "id": m.organization_id,
                "name": m.organization.name,
                "title": m.title,
                "is_primary": m.is_primary,
            }
            for m in memberships
        ]


class PersonWriteSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(required=False, allow_null=True)
    organization_title = serializers.CharField(
        required=False, allow_blank=True, max_length=120, default=""
    )
    owner_id = serializers.IntegerField(required=False, allow_null=True)
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )
    social_urls = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = Person
        fields = [
            "full_name",
            "email",
            "phone",
            "telegram",
            "whatsapp",
            "social_urls",
            "job_title",
            "notes",
            "birth_date",
            "remind_before_days",
            "organization_id",
            "organization_title",
            "owner_id",
            "tag_ids",
        ]

    def create(self, validated_data):
        org_id = validated_data.pop("organization_id", None)
        org_title = validated_data.pop("organization_title", "")
        owner_id = validated_data.pop("owner_id", None)
        tag_ids = validated_data.pop("tag_ids", None)
        workspace = self.context["workspace"]
        owner = None
        if "owner_id" in self.initial_data:
            owner = _owner_in_workspace(workspace, owner_id)
        person = Person.objects.create(workspace=workspace, owner=owner, **validated_data)
        if org_id:
            org = Organization.objects.filter(workspace=workspace, pk=org_id).first()
            if org is None:
                raise serializers.ValidationError({"organization_id": "Not found."})
            OrganizationMembership.objects.create(
                organization=org,
                person=person,
                title=org_title or "",
                is_primary=True,
            )
        if tag_ids is not None:
            self._sync_tags(person, tag_ids)
        return person

    def update(self, instance, validated_data):
        org_id = validated_data.pop("organization_id", None)
        org_title = validated_data.pop("organization_title", None)
        owner_id = validated_data.pop("owner_id", None)
        tag_ids = validated_data.pop("tag_ids", None)
        org_provided = "organization_id" in self.initial_data
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if "owner_id" in self.initial_data:
            instance.owner = _owner_in_workspace(instance.workspace, owner_id)
        instance.save()
        if org_provided:
            if org_id is None:
                instance.organization_memberships.all().delete()
            else:
                org = Organization.objects.filter(
                    workspace=self.context["workspace"], pk=org_id
                ).first()
                if org is None:
                    raise serializers.ValidationError({"organization_id": "Not found."})
                membership, _ = OrganizationMembership.objects.update_or_create(
                    organization=org,
                    person=instance,
                    defaults={
                        "title": org_title if org_title is not None else "",
                        "is_primary": True,
                    },
                )
                instance.organization_memberships.exclude(pk=membership.pk).update(
                    is_primary=False
                )
        elif org_title is not None:
            primary = instance.organization_memberships.filter(is_primary=True).first()
            if primary:
                primary.title = org_title
                primary.save(update_fields=["title"])
        if tag_ids is not None:
            self._sync_tags(instance, tag_ids)
        return instance

    def _sync_tags(self, person, tag_ids):
        workspace = person.workspace
        valid = set(
            Tag.objects.filter(workspace=workspace, id__in=tag_ids).values_list("id", flat=True)
        )
        PersonTag.objects.filter(person=person).exclude(tag_id__in=valid).delete()
        existing = set(
            PersonTag.objects.filter(person=person).values_list("tag_id", flat=True)
        )
        for tag_id in valid - existing:
            PersonTag.objects.create(person=person, tag_id=tag_id)


class ProjectPersonLinkSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source="person.full_name", read_only=True)
    person_email = serializers.EmailField(source="person.email", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = ProjectPersonLink
        fields = [
            "id",
            "project",
            "project_name",
            "person",
            "person_name",
            "person_email",
            "role_kind",
            "role_label",
            "interest",
            "influence",
            "notes",
            "stakeholder_id",
            "created_at",
        ]
        read_only_fields = fields


class ProjectPersonLinkWriteSerializer(serializers.Serializer):
    person_id = serializers.IntegerField()
    role_kind = serializers.ChoiceField(
        choices=ProjectPersonLink.RoleKind.choices,
        default=ProjectPersonLink.RoleKind.STAKEHOLDER,
    )
    role_label = serializers.CharField(required=False, allow_blank=True, max_length=255)
    interest = serializers.IntegerField(required=False, min_value=1, max_value=5, default=3)
    influence = serializers.IntegerField(required=False, min_value=1, max_value=5, default=3)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ActivitySerializer(serializers.ModelSerializer):
    created_by_email = serializers.SerializerMethodField()
    person_name = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            "id",
            "kind",
            "subject",
            "body",
            "occurred_at",
            "person",
            "person_name",
            "organization",
            "organization_name",
            "project",
            "project_name",
            "created_by",
            "created_by_email",
            "created_at",
        ]
        read_only_fields = fields

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by_id else None

    def get_person_name(self, obj):
        return obj.person.full_name if obj.person_id else None

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization_id else None

    def get_project_name(self, obj):
        return obj.project.name if obj.project_id else None


class ActivityWriteSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=Activity.Kind.choices, default=Activity.Kind.NOTE)
    subject = serializers.CharField(max_length=255)
    body = serializers.CharField(required=False, allow_blank=True, default="")
    occurred_at = serializers.DateTimeField(required=False)
    person_id = serializers.IntegerField(required=False, allow_null=True)
    organization_id = serializers.IntegerField(required=False, allow_null=True)
    project_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("person_id") and not attrs.get("organization_id"):
            raise serializers.ValidationError(
                "person_id or organization_id is required."
            )
        return attrs

    def create(self, validated_data):
        workspace = self.context["workspace"]
        person_id = validated_data.get("person_id")
        org_id = validated_data.get("organization_id")
        project_id = validated_data.get("project_id")
        person = None
        organization = None
        project = None
        if person_id:
            person = Person.objects.filter(workspace=workspace, pk=person_id).first()
            if person is None:
                raise serializers.ValidationError({"person_id": "Not found."})
        if org_id:
            organization = Organization.objects.filter(
                workspace=workspace, pk=org_id
            ).first()
            if organization is None:
                raise serializers.ValidationError({"organization_id": "Not found."})
        if project_id:
            project = Project.objects.filter(workspace=workspace, pk=project_id).first()
            if project is None:
                raise serializers.ValidationError({"project_id": "Not found."})
        return Activity.objects.create(
            workspace=workspace,
            kind=validated_data["kind"],
            subject=validated_data["subject"],
            body=validated_data.get("body", ""),
            occurred_at=validated_data.get("occurred_at") or timezone.now(),
            person=person,
            organization=organization,
            project=project,
            created_by=self.context["request"].user,
        )


class SegmentSerializer(serializers.ModelSerializer):
    people_count = serializers.SerializerMethodField()
    organizations_count = serializers.SerializerMethodField()

    class Meta:
        model = Segment
        fields = [
            "id",
            "name",
            "kind",
            "rule",
            "people_count",
            "organizations_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_people_count(self, obj):
        from crm.services import resolve_segment_people

        return resolve_segment_people(obj).count()

    def get_organizations_count(self, obj):
        from crm.services import resolve_segment_organizations

        return resolve_segment_organizations(obj).count()


class SegmentWriteSerializer(serializers.ModelSerializer):
    person_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )
    organization_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )

    class Meta:
        model = Segment
        fields = ["name", "kind", "rule", "person_ids", "organization_ids"]

    def create(self, validated_data):
        person_ids = validated_data.pop("person_ids", [])
        organization_ids = validated_data.pop("organization_ids", [])
        workspace = self.context["workspace"]
        segment = Segment.objects.create(workspace=workspace, **validated_data)
        self._sync_members(segment, person_ids, organization_ids)
        return segment

    def update(self, instance, validated_data):
        person_ids = validated_data.pop("person_ids", None)
        organization_ids = validated_data.pop("organization_ids", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if person_ids is not None or organization_ids is not None:
            self._sync_members(
                instance,
                person_ids if person_ids is not None else list(
                    instance.people.values_list("id", flat=True)
                ),
                organization_ids
                if organization_ids is not None
                else list(instance.organizations.values_list("id", flat=True)),
            )
        return instance

    def _sync_members(self, segment, person_ids, organization_ids):
        workspace = segment.workspace
        people = Person.objects.filter(workspace=workspace, id__in=person_ids)
        orgs = Organization.objects.filter(workspace=workspace, id__in=organization_ids)
        segment.people.set(people)
        segment.organizations.set(orgs)


class CrmCommentSerializer(serializers.ModelSerializer):
    author_email = serializers.SerializerMethodField()

    class Meta:
        model = CrmComment
        fields = [
            "id",
            "body",
            "person",
            "organization",
            "author",
            "author_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_author_email(self, obj):
        return obj.author.email if obj.author_id else None


class CrmCommentWriteSerializer(serializers.Serializer):
    body = serializers.CharField()
    person_id = serializers.IntegerField(required=False, allow_null=True)
    organization_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("person_id") and not attrs.get("organization_id"):
            raise serializers.ValidationError(
                "person_id or organization_id is required."
            )
        if attrs.get("person_id") and attrs.get("organization_id"):
            raise serializers.ValidationError(
                "Provide exactly one of person_id or organization_id."
            )
        return attrs

    def create(self, validated_data):
        workspace = self.context["workspace"]
        person = None
        organization = None
        if validated_data.get("person_id"):
            person = Person.objects.filter(
                workspace=workspace, pk=validated_data["person_id"]
            ).first()
            if person is None:
                raise serializers.ValidationError({"person_id": "Not found."})
        if validated_data.get("organization_id"):
            organization = Organization.objects.filter(
                workspace=workspace, pk=validated_data["organization_id"]
            ).first()
            if organization is None:
                raise serializers.ValidationError({"organization_id": "Not found."})
        return CrmComment.objects.create(
            workspace=workspace,
            person=person,
            organization=organization,
            author=self.context["request"].user,
            body=validated_data["body"],
        )


class CrmAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = CrmAttachment
        fields = [
            "id",
            "name",
            "size",
            "content_type",
            "url",
            "person",
            "organization",
            "uploaded_by",
            "uploaded_by_email",
            "created_at",
        ]
        read_only_fields = fields

    def get_uploaded_by_email(self, obj):
        return obj.uploaded_by.email if obj.uploaded_by_id else None

    def get_url(self, obj):
        try:
            return obj.file.url
        except ValueError:
            return None


class TagAttachSerializer(serializers.Serializer):
    tag_id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False, allow_blank=False, max_length=64)
    color = serializers.CharField(required=False, allow_blank=True, max_length=16)

    def validate(self, attrs):
        if not attrs.get("tag_id") and not attrs.get("name"):
            raise serializers.ValidationError("tag_id or name is required.")
        return attrs

    def resolve_tag(self, workspace):
        if self.validated_data.get("tag_id"):
            tag = Tag.objects.filter(
                workspace=workspace, pk=self.validated_data["tag_id"]
            ).first()
            if tag is None:
                raise serializers.ValidationError({"tag_id": "Not found."})
            return tag
        return get_or_create_tag(
            workspace,
            self.validated_data["name"],
            self.validated_data.get("color") or "#3b82f6",
        )


class PipelineStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineStage
        fields = [
            "id",
            "name",
            "position",
            "default_probability",
            "is_won",
            "is_lost",
        ]
        read_only_fields = fields


class PipelineSerializer(serializers.ModelSerializer):
    stages = PipelineStageSerializer(many=True, read_only=True)

    class Meta:
        model = Pipeline
        fields = ["id", "name", "is_default", "stages", "created_at"]
        read_only_fields = fields


class DealSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    organization_name = serializers.SerializerMethodField()
    person_name = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()
    weighted_amount = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()
    open_tasks_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Deal
        fields = [
            "id",
            "pipeline",
            "stage",
            "stage_name",
            "title",
            "amount",
            "probability",
            "weighted_amount",
            "close_date",
            "organization",
            "organization_name",
            "person",
            "person_name",
            "project",
            "project_name",
            "owner",
            "owner_email",
            "position",
            "notes",
            "is_open",
            "open_tasks_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization_id else None

    def get_person_name(self, obj):
        return obj.person.full_name if obj.person_id else None

    def get_project_name(self, obj):
        return obj.project.name if obj.project_id else None

    def get_owner_email(self, obj):
        return obj.owner.email if obj.owner_id else None

    def get_weighted_amount(self, obj):
        return float(obj.weighted_amount)

    def get_is_open(self, obj):
        return obj.is_open


class DealWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    probability = serializers.IntegerField(required=False, min_value=0, max_value=100)
    close_date = serializers.DateField(required=False, allow_null=True)
    stage_id = serializers.IntegerField(required=False)
    organization_id = serializers.IntegerField(required=False, allow_null=True)
    person_id = serializers.IntegerField(required=False, allow_null=True)
    project_id = serializers.IntegerField(required=False, allow_null=True)
    owner_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    position = serializers.IntegerField(required=False, min_value=0)


class DealMoveSerializer(serializers.Serializer):
    stage_id = serializers.IntegerField()
    position = serializers.IntegerField(required=False, min_value=0)
    probability = serializers.IntegerField(required=False, min_value=0, max_value=100)


class DealTaskSerializer(serializers.ModelSerializer):
    assignee_email = serializers.SerializerMethodField()

    class Meta:
        model = DealTask
        fields = [
            "id",
            "deal",
            "title",
            "due_date",
            "is_done",
            "assignee",
            "assignee_email",
            "remind_before_days",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_assignee_email(self, obj):
        return obj.assignee.email if obj.assignee_id else None


class DealTaskWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    due_date = serializers.DateField(required=False, allow_null=True)
    is_done = serializers.BooleanField(required=False)
    assignee_id = serializers.IntegerField(required=False, allow_null=True)
    remind_before_days = serializers.IntegerField(required=False, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class LeadSerializer(serializers.ModelSerializer):
    assigned_to_email = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    deal_title = serializers.SerializerMethodField()
    duplicate_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, read_only=True
    )

    class Meta:
        model = Lead
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "company_name",
            "source",
            "status",
            "score",
            "assigned_to",
            "assigned_to_email",
            "organization",
            "organization_name",
            "person",
            "deal",
            "deal_title",
            "notes",
            "duplicate_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_assigned_to_email(self, obj):
        return obj.assigned_to.email if obj.assigned_to_id else None

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization_id else None

    def get_deal_title(self, obj):
        return obj.deal.title if obj.deal_id else None


class LeadWriteSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=64)
    company_name = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )
    source = serializers.CharField(required=False, allow_blank=True, max_length=120)
    status = serializers.ChoiceField(choices=Lead.Status.choices, required=False)
    score = serializers.IntegerField(required=False, min_value=0, max_value=100)
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True)
    organization_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class AutomationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationRule
        fields = [
            "id",
            "name",
            "is_active",
            "trigger",
            "conditions",
            "actions",
            "template_key",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AutomationRuleWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160, required=False)
    is_active = serializers.BooleanField(required=False)
    trigger = serializers.ChoiceField(
        choices=AutomationRule.Trigger.choices,
        required=False,
    )
    conditions = serializers.ListField(required=False, allow_empty=True)
    actions = serializers.ListField(required=False, allow_empty=True)
    template_key = serializers.CharField(required=False, allow_blank=True, max_length=64)


class AutomationRunSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source="rule.name", read_only=True)

    class Meta:
        model = AutomationRun
        fields = [
            "id",
            "rule",
            "rule_name",
            "trigger",
            "context",
            "result",
            "success",
            "created_at",
        ]
        read_only_fields = fields
