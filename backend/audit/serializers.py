from rest_framework import serializers

from audit.models import AuditLogEntry


class AuditLogEntrySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLogEntry
        fields = (
            "id",
            "action",
            "entity_type",
            "entity_id",
            "summary",
            "changes",
            "actor",
            "actor_name",
            "created_at",
        )
        read_only_fields = fields

    def get_actor_name(self, obj):
        if not obj.actor_id:
            return None
        return obj.actor.get_full_name() or obj.actor.email
