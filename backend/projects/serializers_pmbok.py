from rest_framework import serializers

from projects.models import (
    BaselineActivity,
    PhaseGate,
    ProjectBaseline,
    ProjectChangeRequest,
    ProjectCharter,
    ProjectIssue,
    ProjectLessonsLearned,
    RACIEntry,
    Risk,
    Stakeholder,
    WBSQualityCheckItem,
)


class RiskSerializer(serializers.ModelSerializer):
    score = serializers.IntegerField(read_only=True)

    class Meta:
        model = Risk
        fields = (
            "id",
            "title",
            "description",
            "probability",
            "impact",
            "score",
            "status",
            "mitigation",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "score", "created_at", "updated_at")


class RiskWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Risk
        fields = (
            "title",
            "description",
            "probability",
            "impact",
            "status",
            "mitigation",
        )


class ProjectIssueSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(read_only=True, allow_null=True)
    owner_name = serializers.SerializerMethodField()
    related_risk_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = ProjectIssue
        fields = (
            "id",
            "title",
            "description",
            "issue_type",
            "priority",
            "status",
            "owner_id",
            "owner_name",
            "due_date",
            "action",
            "related_risk_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner_id",
            "owner_name",
            "related_risk_id",
            "created_at",
            "updated_at",
        )

    def get_owner_name(self, obj):
        if not obj.owner_id:
            return None
        return obj.owner.get_full_name() or obj.owner.email


class ProjectIssueWriteSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(required=False, allow_null=True)
    related_risk_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = ProjectIssue
        fields = (
            "title",
            "description",
            "issue_type",
            "priority",
            "status",
            "owner_id",
            "due_date",
            "action",
            "related_risk_id",
        )

    def create(self, validated_data):
        owner_id = validated_data.pop("owner_id", serializers.empty)
        related_risk_id = validated_data.pop("related_risk_id", serializers.empty)
        issue = ProjectIssue(**validated_data)
        self._apply_fks(issue, owner_id, related_risk_id)
        issue.save()
        return issue

    def update(self, instance, validated_data):
        owner_id = validated_data.pop("owner_id", serializers.empty)
        related_risk_id = validated_data.pop("related_risk_id", serializers.empty)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        self._apply_fks(instance, owner_id, related_risk_id)
        instance.save()
        return instance

    def _apply_fks(self, issue, owner_id, related_risk_id):
        project = issue.project
        if owner_id is not serializers.empty:
            if owner_id is None:
                issue.owner = None
            else:
                from django.contrib.auth import get_user_model

                User = get_user_model()
                try:
                    issue.owner = User.objects.get(pk=owner_id)
                except User.DoesNotExist as exc:
                    raise serializers.ValidationError(
                        {"owner_id": "User not found."}
                    ) from exc
        if related_risk_id is not serializers.empty:
            if related_risk_id is None:
                issue.related_risk = None
            else:
                try:
                    issue.related_risk = Risk.objects.get(
                        pk=related_risk_id, project=project
                    )
                except Risk.DoesNotExist as exc:
                    raise serializers.ValidationError(
                        {"related_risk_id": "Risk not found on this project."}
                    ) from exc


class StakeholderSerializer(serializers.ModelSerializer):
    person_id = serializers.IntegerField(source="person.id", read_only=True, allow_null=True)

    class Meta:
        model = Stakeholder
        fields = (
            "id",
            "name",
            "role",
            "interest",
            "influence",
            "contact_email",
            "notes",
            "person_id",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "person_id")


class StakeholderWriteSerializer(serializers.ModelSerializer):
    person_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Stakeholder
        fields = (
            "name",
            "role",
            "interest",
            "influence",
            "contact_email",
            "notes",
            "person_id",
        )

    def create(self, validated_data):
        person_id = validated_data.pop("person_id", None)
        stakeholder = super().create(validated_data)
        if person_id:
            self._attach_person(stakeholder, person_id)
        return stakeholder

    def update(self, instance, validated_data):
        person_id = validated_data.pop("person_id", None)
        person_provided = "person_id" in self.initial_data
        stakeholder = super().update(instance, validated_data)
        if person_provided:
            if person_id is None:
                stakeholder.person = None
                stakeholder.save(update_fields=["person"])
            else:
                self._attach_person(stakeholder, person_id)
        return stakeholder

    def _attach_person(self, stakeholder, person_id):
        from crm.models import Person

        person = Person.objects.filter(
            workspace_id=stakeholder.project.workspace_id, pk=person_id
        ).first()
        if person is None:
            raise serializers.ValidationError({"person_id": "Person not found."})
        stakeholder.person = person
        stakeholder.save(update_fields=["person"])


class ProjectCharterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCharter
        fields = (
            "goals",
            "success_criteria",
            "constraints",
            "assumptions",
            "updated_at",
        )
        read_only_fields = ("updated_at",)


class ProjectLessonsLearnedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectLessonsLearned
        fields = (
            "what_went_well",
            "what_went_wrong",
            "recommendations",
            "knowledge_to_reuse",
            "updated_at",
        )
        read_only_fields = ("updated_at",)


class RACIEntrySerializer(serializers.ModelSerializer):
    wbs_code = serializers.CharField(source="wbs_node.code", read_only=True)
    wbs_title = serializers.CharField(source="wbs_node.title", read_only=True)
    stakeholder_name = serializers.CharField(source="stakeholder.name", read_only=True)

    class Meta:
        model = RACIEntry
        fields = (
            "id",
            "wbs_node_id",
            "wbs_code",
            "wbs_title",
            "stakeholder_id",
            "stakeholder_name",
            "raci_type",
        )
        read_only_fields = fields


class RACIWriteSerializer(serializers.Serializer):
    wbs_node_id = serializers.IntegerField()
    stakeholder_id = serializers.IntegerField()
    raci_type = serializers.ChoiceField(choices=RACIEntry.RACIType.choices)


class BaselineActivitySerializer(serializers.ModelSerializer):
    activity_id = serializers.IntegerField(source="activity.id", read_only=True)
    wbs_code = serializers.CharField(source="activity.wbs_node.code", read_only=True)
    wbs_title = serializers.CharField(source="activity.wbs_node.title", read_only=True)

    class Meta:
        model = BaselineActivity
        fields = (
            "id",
            "activity_id",
            "wbs_code",
            "wbs_title",
            "start_date",
            "end_date",
            "duration_days",
            "progress",
        )


class ProjectBaselineSerializer(serializers.ModelSerializer):
    activities = BaselineActivitySerializer(many=True, read_only=True)

    class Meta:
        model = ProjectBaseline
        fields = ("id", "name", "created_at", "created_by", "activities")
        read_only_fields = ("id", "created_at", "created_by", "activities")


class ProjectChangeRequestSerializer(serializers.ModelSerializer):
    baseline_name = serializers.CharField(source="baseline.name", read_only=True, allow_null=True)
    requested_by_email = serializers.EmailField(
        source="requested_by.email", read_only=True, allow_null=True
    )
    decided_by_email = serializers.EmailField(
        source="decided_by.email", read_only=True, allow_null=True
    )

    class Meta:
        model = ProjectChangeRequest
        fields = (
            "id",
            "project",
            "title",
            "description",
            "change_type",
            "status",
            "impact_notes",
            "decision_note",
            "baseline",
            "baseline_name",
            "requested_by",
            "requested_by_email",
            "decided_by",
            "decided_by_email",
            "created_at",
            "updated_at",
            "decided_at",
        )
        read_only_fields = fields


class PhaseGateSerializer(serializers.ModelSerializer):
    phase_title = serializers.CharField(
        source="wbs_phase_node.title", read_only=True
    )
    phase_key = serializers.CharField(
        source="wbs_phase_node.phase_key", read_only=True, allow_null=True
    )
    decided_by_email = serializers.EmailField(
        source="decided_by.email", read_only=True, allow_null=True
    )
    baseline_name = serializers.CharField(
        source="baseline.name", read_only=True, allow_null=True
    )

    class Meta:
        model = PhaseGate
        fields = (
            "id",
            "project",
            "wbs_phase_node",
            "phase_title",
            "phase_key",
            "checklist",
            "decision",
            "comment",
            "decided_by",
            "decided_by_email",
            "decided_at",
            "baseline",
            "baseline_name",
            "process_instance",
        )
        read_only_fields = fields


class WBSQualityCheckItemSerializer(serializers.ModelSerializer):
    checked_by_name = serializers.CharField(
        source="checked_by.get_username", read_only=True, allow_null=True
    )

    class Meta:
        model = WBSQualityCheckItem
        fields = (
            "id",
            "wbs_node",
            "title",
            "result",
            "evidence_url",
            "position",
            "checked_by",
            "checked_by_name",
            "checked_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "wbs_node",
            "checked_by",
            "checked_by_name",
            "checked_at",
            "created_at",
            "updated_at",
        )

