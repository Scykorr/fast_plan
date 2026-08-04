from rest_framework import serializers

from kanban.models import Board, Card, Column


class CardSerializer(serializers.ModelSerializer):
    wbs_node_id = serializers.IntegerField(read_only=True, allow_null=True)
    process_work_node_id = serializers.IntegerField(read_only=True, allow_null=True)
    assignee_id = serializers.SerializerMethodField()
    assignee_name = serializers.SerializerMethodField()
    workflow_status_id = serializers.SerializerMethodField()
    workflow_status_name = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = (
            "id",
            "title",
            "description",
            "position",
            "due_date",
            "created_at",
            "updated_at",
            "wbs_node_id",
            "process_work_node_id",
            "assignee_id",
            "assignee_name",
            "workflow_status_id",
            "workflow_status_name",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "wbs_node_id",
            "process_work_node_id",
            "assignee_id",
            "assignee_name",
            "workflow_status_id",
            "workflow_status_name",
        )

    def _work(self, obj):
        return obj.wbs_node or obj.process_work_node

    def get_assignee_id(self, obj):
        work = self._work(obj)
        return work.assignee_id if work else None

    def get_assignee_name(self, obj):
        work = self._work(obj)
        if not work or not work.assignee:
            return None
        return work.assignee.get_full_name() or work.assignee.email

    def get_workflow_status_id(self, obj):
        wbs = obj.wbs_node
        return wbs.workflow_status_id if wbs else None

    def get_workflow_status_name(self, obj):
        wbs = obj.wbs_node
        if not wbs or not wbs.workflow_status:
            return None
        return wbs.workflow_status.name


class ColumnSerializer(serializers.ModelSerializer):
    cards = CardSerializer(many=True, read_only=True)

    class Meta:
        model = Column
        fields = ("id", "title", "position", "cards")


class BoardListSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(read_only=True, allow_null=True)
    process_instance_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Board
        fields = (
            "id",
            "title",
            "position",
            "created_at",
            "project_id",
            "process_instance_id",
        )


class BoardDetailSerializer(serializers.ModelSerializer):
    columns = serializers.SerializerMethodField()
    project_id = serializers.IntegerField(read_only=True, allow_null=True)
    process_instance_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Board
        fields = (
            "id",
            "title",
            "position",
            "created_at",
            "project_id",
            "process_instance_id",
            "columns",
        )

    def get_columns(self, obj):
        columns = obj.columns.prefetch_related(
            "cards__wbs_node__assignee",
            "cards__wbs_node__workflow_status",
            "cards__process_work_node__assignee",
        ).order_by("position", "id")
        return ColumnSerializer(columns, many=True).data


class BoardWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ("title", "position")


class ColumnWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Column
        fields = ("title", "position")


class CardWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = ("title", "description", "due_date", "position")


class CardMoveSerializer(serializers.Serializer):
    column_id = serializers.IntegerField()
    position = serializers.IntegerField(min_value=0)
