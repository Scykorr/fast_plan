from rest_framework import serializers

from delivery.models import (
    AgentActionLog,
    AgentProfile,
    DeliveryAccessLog,
    DeliveryProjectMeta,
    DeliverySettings,
    DeliverySubTask,
    DeliveryTask,
    Epic,
    Sprint,
    TaskBlocker,
    TaskComment,
    TaskDependency,
    TaskFieldHistory,
    TaskHandoff,
    TaskStatusHistory,
)


class DeliverySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliverySettings
        fields = [
            "agent_ops_enabled",
            "github_webhook_secret",
            "github_api_token",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
        extra_kwargs = {
            "github_webhook_secret": {"write_only": True, "required": False},
            "github_api_token": {"write_only": True, "required": False},
        }


class DeliveryProjectMetaSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    description = serializers.CharField(source="project.description", read_only=True)
    status = serializers.CharField(source="project.status", read_only=True)
    owner = serializers.IntegerField(source="project.manager_id", read_only=True)
    owner_email = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryProjectMeta
        fields = [
            "id",
            "project",
            "project_name",
            "description",
            "status",
            "owner",
            "owner_email",
            "repo_url",
            "docs_url",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project_name",
            "description",
            "status",
            "owner",
            "owner_email",
            "updated_at",
        ]

    def get_owner_email(self, obj):
        manager = getattr(obj.project, "manager", None)
        return manager.email if manager else None


class AgentProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    effective_actions = serializers.SerializerMethodField()
    allowed_project_ids = serializers.PrimaryKeyRelatedField(
        source="allowed_projects",
        many=True,
        read_only=True,
    )

    class Meta:
        model = AgentProfile
        fields = [
            "id",
            "user",
            "user_email",
            "role",
            "actor_type",
            "display_name",
            "is_active",
            "is_service_account",
            "allowed_actions",
            "allowed_project_ids",
            "effective_actions",
            "api_token",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "api_token", "is_service_account"]

    def get_effective_actions(self, obj):
        return obj.effective_actions()


class AgentActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentActionLog
        fields = [
            "id",
            "profile",
            "user",
            "action",
            "entity_type",
            "entity_id",
            "detail",
            "created_at",
        ]


class DeliveryAccessLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAccessLog
        fields = ["id", "user", "method", "path", "status_code", "created_at"]


class EpicSerializer(serializers.ModelSerializer):
    task_ids = serializers.SerializerMethodField()

    class Meta:
        model = Epic
        fields = [
            "id",
            "project",
            "title",
            "description",
            "goal",
            "owner",
            "priority",
            "status",
            "planning_doc_url",
            "task_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "task_ids"]

    def get_task_ids(self, obj):
        return list(obj.tasks.values_list("id", flat=True)[:200])


class SprintSerializer(serializers.ModelSerializer):
    task_count = serializers.SerializerMethodField()
    task_ids = serializers.SerializerMethodField()

    class Meta:
        model = Sprint
        fields = [
            "id",
            "project",
            "name",
            "goal",
            "starts_on",
            "ends_on",
            "capacity",
            "status",
            "task_count",
            "task_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "task_count", "task_ids"]

    def get_task_count(self, obj):
        return obj.tasks.count()

    def get_task_ids(self, obj):
        return list(obj.tasks.values_list("id", flat=True)[:200])


class SubTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliverySubTask
        fields = [
            "id",
            "title",
            "status",
            "assignee",
            "expected_artifact",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class BlockerSerializer(serializers.ModelSerializer):
    is_open = serializers.SerializerMethodField()

    class Meta:
        model = TaskBlocker
        fields = [
            "id",
            "title",
            "detail",
            "needs_owner_decision",
            "created_by",
            "resolved_at",
            "resolved_by",
            "resolution_note",
            "cancelled_at",
            "cancelled_by",
            "cancel_reason",
            "is_open",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "resolved_at",
            "resolved_by",
            "cancelled_at",
            "cancelled_by",
            "created_at",
            "is_open",
        ]

    def get_is_open(self, obj):
        return obj.is_open


class HandoffSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskHandoff
        fields = [
            "id",
            "from_role",
            "to_role",
            "done_summary",
            "left_summary",
            "branch_or_pr_url",
            "checks_url",
            "open_questions",
            "needs_owner_decision",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_at"]


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = ["id", "kind", "body", "author", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatusHistory
        fields = [
            "id",
            "from_status",
            "to_status",
            "changed_by",
            "reason",
            "created_at",
        ]


class FieldHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskFieldHistory
        fields = [
            "id",
            "field",
            "old_value",
            "new_value",
            "changed_by",
            "created_at",
        ]


class DependencySerializer(serializers.ModelSerializer):
    depends_on_title = serializers.CharField(
        source="depends_on.title", read_only=True
    )
    depends_on_status = serializers.CharField(
        source="depends_on.status", read_only=True
    )

    class Meta:
        model = TaskDependency
        fields = [
            "id",
            "depends_on",
            "depends_on_title",
            "depends_on_status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DeliveryTaskSerializer(serializers.ModelSerializer):
    subtasks = SubTaskSerializer(many=True, read_only=True)
    blockers = BlockerSerializer(many=True, read_only=True)
    handoffs = HandoffSerializer(many=True, read_only=True)
    dependencies = DependencySerializer(many=True, read_only=True)
    open_blockers_count = serializers.SerializerMethodField()
    assignee_email = serializers.SerializerMethodField()
    ready_missing = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryTask
        fields = [
            "id",
            "project",
            "epic",
            "sprint",
            "title",
            "description",
            "business_outcome",
            "context",
            "task_type",
            "priority",
            "status",
            "assignee_role",
            "assignee",
            "assignee_email",
            "created_by",
            "ready_criterion",
            "done_criterion",
            "scope_in",
            "scope_out",
            "expected_checks",
            "result_artifact",
            "next_role",
            "canon_url",
            "architecture_url",
            "planning_doc_url",
            "acceptance_url",
            "external_pack_url",
            "github_repo",
            "github_branch",
            "github_commit",
            "github_pr_url",
            "github_pr_number",
            "github_pr_state",
            "github_checks_url",
            "github_checks_status",
            "github_review_notes",
            "version",
            "subtasks",
            "blockers",
            "handoffs",
            "dependencies",
            "open_blockers_count",
            "ready_missing",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "version",
            "subtasks",
            "blockers",
            "handoffs",
            "dependencies",
            "open_blockers_count",
            "ready_missing",
            "created_at",
            "updated_at",
        ]

    def get_open_blockers_count(self, obj):
        return obj.blockers.filter(
            resolved_at__isnull=True, cancelled_at__isnull=True
        ).count()

    def get_assignee_email(self, obj):
        return obj.assignee.email if obj.assignee_id else None

    def get_ready_missing(self, obj):
        from delivery.services import ready_gate_errors

        return ready_gate_errors(obj)


class DeliveryTaskWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTask
        fields = [
            "project",
            "epic",
            "sprint",
            "title",
            "description",
            "business_outcome",
            "context",
            "task_type",
            "priority",
            "assignee_role",
            "assignee",
            "ready_criterion",
            "done_criterion",
            "scope_in",
            "scope_out",
            "expected_checks",
            "result_artifact",
            "next_role",
            "canon_url",
            "architecture_url",
            "planning_doc_url",
            "acceptance_url",
            "external_pack_url",
            "github_repo",
            "github_branch",
            "github_commit",
            "github_pr_url",
            "github_pr_number",
            "github_pr_state",
            "github_checks_url",
            "github_checks_status",
            "github_review_notes",
        ]
