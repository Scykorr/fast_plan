from rest_framework import serializers

from timelog.models import TimeEntry


class TimeEntrySerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    wbs_code = serializers.CharField(source="wbs_node.code", read_only=True)
    wbs_title = serializers.CharField(source="wbs_node.title", read_only=True)

    class Meta:
        model = TimeEntry
        fields = (
            "id",
            "user",
            "user_name",
            "wbs_node",
            "wbs_code",
            "wbs_title",
            "hours",
            "work_date",
            "notes",
            "created_at",
        )
        read_only_fields = ("id", "user", "user_name", "wbs_code", "wbs_title", "created_at")

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email


class TimeEntryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry
        fields = ("wbs_node", "hours", "work_date", "notes")

    def validate_hours(self, value):
        if value <= 0:
            raise serializers.ValidationError("Hours must be positive.")
        return value
