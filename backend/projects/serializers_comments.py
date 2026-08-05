from rest_framework import serializers

from projects.models import WorkItemComment


class WorkItemCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    wbs_node_id = serializers.IntegerField(read_only=True, allow_null=True)
    card_id = serializers.IntegerField(read_only=True, allow_null=True)
    process_work_node_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = WorkItemComment
        fields = (
            "id",
            "kind",
            "body",
            "author",
            "author_name",
            "wbs_node_id",
            "card_id",
            "process_work_node_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.email


class WorkItemCommentWriteSerializer(serializers.Serializer):
    body = serializers.CharField()
    kind = serializers.ChoiceField(
        choices=WorkItemComment.Kind.choices,
        default=WorkItemComment.Kind.COMMENT,
    )
