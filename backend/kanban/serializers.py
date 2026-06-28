from rest_framework import serializers

from kanban.models import Board, Card, Column


class CardSerializer(serializers.ModelSerializer):
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
        )
        read_only_fields = ("id", "created_at", "updated_at")


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
    columns = ColumnSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ("id", "title", "position", "created_at", "columns")


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
