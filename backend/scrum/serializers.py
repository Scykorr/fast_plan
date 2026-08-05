from rest_framework import serializers

from scrum.models import ProductBacklogItem, ScrumSprint


class ScrumSprintSerializer(serializers.ModelSerializer):
    pbi_count = serializers.SerializerMethodField()
    committed_points = serializers.SerializerMethodField()
    remaining_points = serializers.SerializerMethodField()

    class Meta:
        model = ScrumSprint
        fields = (
            "id",
            "name",
            "goal",
            "starts_on",
            "ends_on",
            "status",
            "pbi_count",
            "committed_points",
            "remaining_points",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "pbi_count",
            "committed_points",
            "remaining_points",
            "created_at",
            "updated_at",
        )

    def get_pbi_count(self, obj):
        return obj.pbis.count()

    def get_committed_points(self, obj):
        return sum(p.story_points or 0 for p in obj.pbis.all())

    def get_remaining_points(self, obj):
        return sum(
            p.story_points or 0
            for p in obj.pbis.all()
            if p.status != ProductBacklogItem.Status.DONE
        )


class ScrumSprintWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrumSprint
        fields = ("name", "goal", "starts_on", "ends_on", "status")


class ProductBacklogItemSerializer(serializers.ModelSerializer):
    assignee_id = serializers.IntegerField(read_only=True, allow_null=True)
    assignee_name = serializers.SerializerMethodField()
    sprint_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = ProductBacklogItem
        fields = (
            "id",
            "title",
            "description",
            "story_points",
            "priority",
            "rank",
            "status",
            "sprint_id",
            "assignee_id",
            "assignee_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_assignee_name(self, obj):
        if not obj.assignee_id:
            return None
        return obj.assignee.get_full_name() or obj.assignee.email


class ProductBacklogItemWriteSerializer(serializers.ModelSerializer):
    assignee_id = serializers.IntegerField(required=False, allow_null=True)
    sprint_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = ProductBacklogItem
        fields = (
            "title",
            "description",
            "story_points",
            "priority",
            "rank",
            "status",
            "assignee_id",
            "sprint_id",
        )

    def create(self, validated_data):
        assignee_id = validated_data.pop("assignee_id", serializers.empty)
        sprint_id = validated_data.pop("sprint_id", serializers.empty)
        item = ProductBacklogItem(**validated_data)
        self._apply_fks(item, assignee_id, sprint_id)
        item.save()
        return item

    def update(self, instance, validated_data):
        assignee_id = validated_data.pop("assignee_id", serializers.empty)
        sprint_id = validated_data.pop("sprint_id", serializers.empty)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        self._apply_fks(instance, assignee_id, sprint_id)
        instance.save()
        return instance

    def _apply_fks(self, item, assignee_id, sprint_id):
        if assignee_id is not serializers.empty:
            if assignee_id is None:
                item.assignee = None
            else:
                from django.contrib.auth import get_user_model

                User = get_user_model()
                try:
                    item.assignee = User.objects.get(pk=assignee_id)
                except User.DoesNotExist as exc:
                    raise serializers.ValidationError(
                        {"assignee_id": "User not found."}
                    ) from exc
        if sprint_id is not serializers.empty:
            if sprint_id is None:
                item.sprint = None
            else:
                try:
                    item.sprint = ScrumSprint.objects.get(
                        pk=sprint_id, project=item.project
                    )
                except ScrumSprint.DoesNotExist as exc:
                    raise serializers.ValidationError(
                        {"sprint_id": "Sprint not found on this project."}
                    ) from exc
