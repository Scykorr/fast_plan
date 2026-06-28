from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from projects.models import ActivityDependency, Project, ScheduleActivity, WBSNode
from projects.services import move_wbs_node


class ProjectListSerializer(serializers.ModelSerializer):
    wbs_count = serializers.SerializerMethodField()
    board_id = serializers.SerializerMethodField()
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
            "budget",
            "manager",
            "created_at",
            "updated_at",
            "wbs_count",
            "progress",
            "board_id",
        )
        read_only_fields = ("id", "created_at", "updated_at", "wbs_count", "progress", "board_id")

    def get_wbs_count(self, obj):
        return obj.wbs_nodes.count()

    def get_progress(self, obj):
        activities = ScheduleActivity.objects.filter(wbs_node__project=obj)
        if not activities.exists():
            return 0
        return round(sum(a.progress for a in activities) / activities.count())

    def get_board_id(self, obj):
        board = getattr(obj, "board", None)
        return board.id if board else None


class ProjectWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            "name",
            "description",
            "status",
            "start_date",
            "end_date",
            "budget",
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
    parent_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = WBSNode
        fields = ("title", "description", "node_type", "position", "parent_id")

    def update(self, instance, validated_data):
        parent_id = validated_data.pop("parent_id", None)
        position = validated_data.pop("position", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if validated_data:
            instance.save()

        if parent_id is not None or position is not None:
            target_parent = parent_id if parent_id is not None else instance.parent_id
            if position is not None:
                target_position = position
            elif parent_id is not None and parent_id != instance.parent_id:
                target_position = (
                    WBSNode.objects.filter(
                        parent_id=target_parent,
                        project=instance.project,
                    )
                    .exclude(pk=instance.pk)
                    .count()
                )
            else:
                target_position = instance.position
            try:
                move_wbs_node(
                    instance,
                    parent_id=target_parent,
                    position=target_position,
                )
            except DjangoValidationError as exc:
                raise serializers.ValidationError(str(exc)) from exc

        instance.refresh_from_db()
        return instance


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
