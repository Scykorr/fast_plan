from rest_framework import serializers

from process.models import (
    CaseDefinition,
    CaseInstance,
    DecisionDefinition,
    ProcessDefinition,
    ProcessDeployment,
    ProcessInstance,
    UserTask,
)


class ProcessDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessDefinition
        fields = (
            "id",
            "key",
            "name",
            "description",
            "bpmn_xml",
            "process_id",
            "version",
            "is_published",
            "category",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at", "version")


class ProcessDeploymentSerializer(serializers.ModelSerializer):
    definition_key = serializers.CharField(source="definition.key", read_only=True)

    class Meta:
        model = ProcessDeployment
        fields = (
            "id",
            "definition",
            "definition_key",
            "version",
            "process_id",
            "deployed_at",
        )


class ProcessInstanceSerializer(serializers.ModelSerializer):
    definition_name = serializers.CharField(
        source="deployment.definition.name", read_only=True
    )
    definition_key = serializers.CharField(
        source="deployment.definition.key", read_only=True
    )

    class Meta:
        model = ProcessInstance
        fields = (
            "id",
            "deployment",
            "definition_name",
            "definition_key",
            "business_key",
            "deal",
            "project",
            "organization",
            "status",
            "data",
            "error_message",
            "started_at",
            "completed_at",
        )
        read_only_fields = fields


class UserTaskSerializer(serializers.ModelSerializer):
    instance_id = serializers.IntegerField(source="instance.id", read_only=True)
    definition_name = serializers.CharField(
        source="instance.deployment.definition.name", read_only=True
    )
    deal = serializers.IntegerField(source="instance.deal_id", read_only=True)
    project = serializers.IntegerField(source="instance.project_id", read_only=True)

    class Meta:
        model = UserTask
        fields = (
            "id",
            "instance_id",
            "definition_name",
            "name",
            "description",
            "status",
            "assignee",
            "candidate_role",
            "form_schema",
            "form_data",
            "due_at",
            "created_at",
            "completed_at",
            "deal",
            "project",
        )
        read_only_fields = (
            "id",
            "instance_id",
            "definition_name",
            "status",
            "created_at",
            "completed_at",
            "deal",
            "project",
        )


class DecisionDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionDefinition
        fields = (
            "id",
            "key",
            "name",
            "dmn_xml",
            "decision_id",
            "version",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at", "version")


class CaseDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseDefinition
        fields = (
            "id",
            "key",
            "name",
            "description",
            "plan_items",
            "cmmn_xml",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class CaseInstanceSerializer(serializers.ModelSerializer):
    definition_name = serializers.CharField(source="definition.name", read_only=True)
    available_items = serializers.SerializerMethodField()
    required_incomplete = serializers.SerializerMethodField()

    class Meta:
        model = CaseInstance
        fields = (
            "id",
            "definition",
            "definition_name",
            "title",
            "status",
            "deal",
            "project",
            "completed_items",
            "available_items",
            "required_incomplete",
            "data",
            "started_at",
            "closed_at",
        )
        read_only_fields = (
            "id",
            "definition_name",
            "status",
            "completed_items",
            "available_items",
            "required_incomplete",
            "started_at",
            "closed_at",
        )

    def get_available_items(self, obj):
        from process.cases import available_items

        return available_items(obj)

    def get_required_incomplete(self, obj):
        from process.cases import required_incomplete

        return required_incomplete(obj)
