from rest_framework import serializers

from attachments.models import WorkItemAttachment


class WorkItemAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    wbs_node_id = serializers.IntegerField(source="wbs_node.id", read_only=True, allow_null=True)
    card_id = serializers.IntegerField(source="card.id", read_only=True, allow_null=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = WorkItemAttachment
        fields = (
            "id",
            "name",
            "size",
            "content_type",
            "url",
            "uploaded_by",
            "uploaded_by_name",
            "wbs_node_id",
            "card_id",
            "created_at",
        )
        read_only_fields = fields

    def get_uploaded_by_name(self, obj):
        if not obj.uploaded_by_id:
            return None
        return obj.uploaded_by.get_full_name() or obj.uploaded_by.email

    def get_url(self, obj):
        try:
            return obj.file.url
        except ValueError:
            return None
