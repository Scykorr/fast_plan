from rest_framework import serializers

from projects.models import (
    BaselineActivity,
    ProjectBaseline,
    ProjectCharter,
    RACIEntry,
    Risk,
    Stakeholder,
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


class StakeholderSerializer(serializers.ModelSerializer):
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
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class StakeholderWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stakeholder
        fields = ("name", "role", "interest", "influence", "contact_email", "notes")


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
