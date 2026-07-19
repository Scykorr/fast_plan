from rest_framework import serializers

from kanban.models import Board, Card, Column


class CardSerializer(serializers.ModelSerializer):
    wbs_node_id = serializers.IntegerField(
        source="wbs_node.id",
        read_only=True,
        allow_null=True,
    )
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
            "assignee_id",
            "assignee_name",
            "workflow_status_id",
            "workflow_status_name",
        )

    def _wbs(self, obj):
        return getattr(obj, "wbs_node", None)

    def get_assignee_id(self, obj):
        wbs = self._wbs(obj)
        return wbs.assignee_id if wbs else None

    def get_assignee_name(self, obj):
        wbs = self._wbs(obj)
        if not wbs or not wbs.assignee:
            return None
        return wbs.assignee.get_full_name() or wbs.assignee.email

    def get_workflow_status_id(self, obj):
        wbs = self._wbs(obj)
        return wbs.workflow_status_id if wbs else None

    def get_workflow_status_name(self, obj):
        wbs = self._wbs(obj)
        if not wbs or not wbs.workflow_status:
            return None
        return wbs.workflow_status.name


class ColumnSerializer(serializers.ModelSerializer):
    cards = CardSerializer(many=True, read_only=True)

    class Meta:
        model = Column
        fields = ("id", "title", "position", "cards")


class BoardListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ("id", "title", "position", "created_at")


class BoardDetailSerializer(serializers.ModelSerializer):
    columns = serializers.SerializerMethodField()

    class Meta:
        model = Board
        fields = ("id", "title", "position", "created_at", "columns")

    def get_columns(self, obj):
        columns = obj.columns.prefetch_related(
            "cards__wbs_node__assignee",
            "cards__wbs_node__workflow_status",
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
