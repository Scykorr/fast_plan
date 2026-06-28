from rest_framework import serializers

from projects.models import ActivityDependency, Project, ScheduleActivity, WBSNode


class ProjectListSerializer(serializers.ModelSerializer):
    wbs_count = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "description",
            "status",
            "start_date",
            "end_date",
            "manager",
            "created_at",
            "updated_at",
            "wbs_count",
            "progress",
        )
        read_only_fields = ("id", "created_at", "updated_at", "wbs_count", "progress")

    def get_wbs_count(self, obj):
        return obj.wbs_nodes.count()

    def get_progress(self, obj):
        activities = ScheduleActivity.objects.filter(wbs_node__project=obj)
        if not activities.exists():
            return 0
        return round(sum(a.progress for a in activities) / activities.count())


class ProjectWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            "name",
            "description",
            "status",
            "start_date",
            "end_date",
            "manager",
        )


class WBSNodeWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    node_type = serializers.ChoiceField(
        choices=WBSNode.NodeType.choices,
        default=WBSNode.NodeType.WORK_PACKAGE,
    )
    parent_id = serializers.IntegerField(required=False, allow_null=True)


class WBSNodeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WBSNode
        fields = ("title", "description", "node_type", "position", "parent_id")


class ScheduleActivitySerializer(serializers.ModelSerializer):
    wbs_id = serializers.IntegerField(source="wbs_node_id", read_only=True)
    name = serializers.CharField(source="wbs_node.title", read_only=True)
    code = serializers.CharField(source="wbs_node.code", read_only=True)

    class Meta:
        model = ScheduleActivity
        fields = (
            "id",
            "wbs_id",
            "name",
            "code",
            "start_date",
            "end_date",
            "duration_days",
            "progress",
            "is_milestone",
        )


class ScheduleActivityUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleActivity
        fields = (
            "start_date",
            "end_date",
            "duration_days",
            "progress",
            "is_milestone",
        )


class ActivityDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityDependency
        fields = (
            "id",
            "predecessor_id",
            "successor_id",
            "dependency_type",
            "lag_days",
        )


class ActivityDependencyWriteSerializer(serializers.Serializer):
    predecessor_id = serializers.IntegerField()
    successor_id = serializers.IntegerField()
    dependency_type = serializers.ChoiceField(
        choices=ActivityDependency.DependencyType.choices,
        default=ActivityDependency.DependencyType.FS,
    )
    lag_days = serializers.IntegerField(default=0)
