from rest_framework import serializers

from timelog.models import TimeEntry


class TimeEntrySerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    wbs_code = serializers.SerializerMethodField()
    wbs_title = serializers.SerializerMethodField()
    process_work_node_title = serializers.SerializerMethodField()

    class Meta:
        model = TimeEntry
        fields = (
            "id",
            "user",
            "user_name",
            "wbs_node",
            "wbs_code",
            "wbs_title",
            "process_work_node",
            "process_work_node_title",
            "hours",
            "work_date",
            "notes",
            "created_at",
        )
        read_only_fields = (
            "id",
            "user",
            "user_name",
            "wbs_code",
            "wbs_title",
            "process_work_node_title",
            "created_at",
        )

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_wbs_code(self, obj):
        return obj.wbs_node.code if obj.wbs_node_id else None

    def get_wbs_title(self, obj):
        return obj.wbs_node.title if obj.wbs_node_id else None

    def get_process_work_node_title(self, obj):
        return obj.process_work_node.title if obj.process_work_node_id else None


class TimeEntryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry
        fields = ("wbs_node", "process_work_node", "hours", "work_date", "notes")
        extra_kwargs = {
            "wbs_node": {"required": False, "allow_null": True},
            "process_work_node": {"required": False, "allow_null": True},
        }

    def validate_hours(self, value):
        if value <= 0:
            raise serializers.ValidationError("Hours must be positive.")
        return value

    def validate(self, attrs):
        wbs = attrs.get("wbs_node", getattr(self.instance, "wbs_node", None))
        pwn = attrs.get(
            "process_work_node", getattr(self.instance, "process_work_node", None)
        )
        if self.partial and "wbs_node" not in attrs and "process_work_node" not in attrs:
            return attrs
        if bool(wbs) == bool(pwn):
            raise serializers.ValidationError(
                "Provide exactly one of wbs_node or process_work_node."
            )
        return attrs
