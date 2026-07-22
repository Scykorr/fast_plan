from django.utils import timezone
from rest_framework import serializers

from crm.models import (
    Activity,
    Organization,
    OrganizationMembership,
    Person,
    ProjectPersonLink,
)
from projects.models import Project


class OrganizationSerializer(serializers.ModelSerializer):
    people_count = serializers.IntegerField(read_only=True, required=False)
    projects_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "website",
            "industry",
            "notes",
            "people_count",
            "projects_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "people_count", "projects_count"]


class OrganizationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name", "website", "industry", "notes"]

    def create(self, validated_data):
        return Organization.objects.create(
            workspace=self.context["workspace"],
            **validated_data,
        )


class PersonSerializer(serializers.ModelSerializer):
    organizations = serializers.SerializerMethodField()
    projects_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Person
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "job_title",
            "notes",
            "birth_date",
            "remind_before_days",
            "organizations",
            "projects_count",
            "legacy_contact_id",
            "user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

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

    class Meta:
        model = Person
        fields = [
            "full_name",
            "email",
            "phone",
            "job_title",
            "notes",
            "birth_date",
            "remind_before_days",
            "organization_id",
            "organization_title",
        ]

    def create(self, validated_data):
        org_id = validated_data.pop("organization_id", None)
        org_title = validated_data.pop("organization_title", "")
        person = Person.objects.create(
            workspace=self.context["workspace"],
            **validated_data,
        )
        if org_id:
            org = Organization.objects.filter(
                workspace=self.context["workspace"], pk=org_id
            ).first()
            if org is None:
                raise serializers.ValidationError({"organization_id": "Not found."})
            OrganizationMembership.objects.create(
                organization=org,
                person=person,
                title=org_title or "",
                is_primary=True,
            )
        return person

    def update(self, instance, validated_data):
        org_id = validated_data.pop("organization_id", None)
        org_title = validated_data.pop("organization_title", None)
        org_provided = "organization_id" in self.initial_data
        for key, value in validated_data.items():
            setattr(instance, key, value)
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
        return instance


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
