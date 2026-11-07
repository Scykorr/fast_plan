from rest_framework import serializers

from ladya.models import (
    IntakeRequest,
    Laboratory,
    LadyaSettings,
    Package,
    PackageFile,
    PackageStatusEvent,
)
from ladya.services import next_package_number


class LadyaSettingsSerializer(serializers.ModelSerializer):
    package_max_bytes = serializers.SerializerMethodField()
    telegram_webhook_secret_set = serializers.SerializerMethodField()
    telegram_webhook_path = serializers.SerializerMethodField()

    class Meta:
        model = LadyaSettings
        fields = (
            "ladya_hub_enabled",
            "package_max_bytes",
            "telegram_webhook_secret_set",
            "telegram_webhook_path",
            "updated_at",
        )
        read_only_fields = (
            "updated_at",
            "package_max_bytes",
            "telegram_webhook_secret_set",
            "telegram_webhook_path",
        )

    def get_package_max_bytes(self, _obj) -> int:
        from django.conf import settings

        return int(getattr(settings, "LADYA_PACKAGE_MAX_BYTES", 256 * 1024 * 1024))

    def get_telegram_webhook_secret_set(self, obj) -> bool:
        return bool(obj.telegram_webhook_secret)

    def get_telegram_webhook_path(self, obj) -> str:
        if not obj.telegram_webhook_secret:
            return ""
        return f"/api/ladya/telegram/{obj.telegram_webhook_secret}/"


class LaboratorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Laboratory
        fields = (
            "id",
            "slug",
            "title",
            "kind",
            "is_active",
            "chat_room",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class LaboratoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Laboratory
        fields = ("slug", "title", "kind", "is_active", "chat_room")

    def validate_chat_room(self, value):
        if value is None:
            return value
        workspace = self.context["workspace"]
        # Room must belong to this workspace (direct or via project).
        if value.workspace_id and value.workspace_id != workspace.id:
            raise serializers.ValidationError("Чат из другого workspace.")
        if value.project_id and value.project.workspace_id != workspace.id:
            raise serializers.ValidationError("Чат проекта из другого workspace.")
        return value

    def create(self, validated_data):
        return Laboratory.objects.create(
            workspace=self.context["workspace"],
            **validated_data,
        )


class PackageFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageFile
        fields = (
            "id",
            "original_name",
            "size",
            "sha256",
            "content_type",
            "uploaded_by",
            "created_at",
            "file",
        )
        read_only_fields = fields


class PackageStatusEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageStatusEvent
        fields = (
            "id",
            "from_status",
            "to_status",
            "from_laboratory",
            "to_laboratory",
            "reason",
            "changed_by",
            "created_at",
        )
        read_only_fields = fields


class PackageSerializer(serializers.ModelSerializer):
    display_code = serializers.CharField(read_only=True)
    files = PackageFileSerializer(many=True, read_only=True)
    status_events = PackageStatusEventSerializer(many=True, read_only=True)

    class Meta:
        model = Package
        fields = (
            "id",
            "public_number",
            "display_code",
            "title",
            "summary",
            "from_laboratory",
            "to_laboratory",
            "status",
            "created_by",
            "linked_delivery_task",
            "preferred_role",
            "manifest_sha256",
            "notes_limitations",
            "created_at",
            "updated_at",
            "files",
            "status_events",
        )
        read_only_fields = (
            "id",
            "public_number",
            "display_code",
            "status",
            "created_by",
            "created_at",
            "updated_at",
            "files",
            "status_events",
        )


class PackageWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    summary = serializers.CharField(required=False, allow_blank=True, default="")
    from_laboratory = serializers.IntegerField(required=False, allow_null=True)
    to_laboratory = serializers.IntegerField(required=False, allow_null=True)
    linked_delivery_task = serializers.IntegerField(required=False, allow_null=True)
    preferred_role = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=32
    )
    manifest_sha256 = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=64
    )
    notes_limitations = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def _lab(self, lab_id):
        if lab_id is None:
            return None
        workspace = self.context["workspace"]
        try:
            return Laboratory.objects.get(pk=lab_id, workspace=workspace)
        except Laboratory.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"detail": f"Лаборатория {lab_id} не найдена."}
            ) from exc

    def _task(self, task_id):
        if task_id is None:
            return None
        from delivery.models import DeliveryTask

        workspace = self.context["workspace"]
        try:
            return DeliveryTask.objects.get(pk=task_id, workspace=workspace)
        except DeliveryTask.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"linked_delivery_task": f"Задача {task_id} не найдена."}
            ) from exc

    def create(self, validated_data):
        workspace = self.context["workspace"]
        user = self.context["user"]
        package = Package.objects.create(
            workspace=workspace,
            public_number=next_package_number(workspace),
            title=validated_data["title"],
            summary=validated_data.get("summary", ""),
            from_laboratory=self._lab(validated_data.get("from_laboratory")),
            to_laboratory=self._lab(validated_data.get("to_laboratory")),
            linked_delivery_task=self._task(validated_data.get("linked_delivery_task")),
            preferred_role=validated_data.get("preferred_role", ""),
            manifest_sha256=validated_data.get("manifest_sha256", ""),
            notes_limitations=validated_data.get("notes_limitations", ""),
            created_by=user,
            status=Package.Status.DRAFT,
        )
        PackageStatusEvent.objects.create(
            package=package,
            from_status="",
            to_status=Package.Status.DRAFT,
            to_laboratory=package.to_laboratory,
            reason="Создан",
            changed_by=user,
        )
        return package

    def update(self, instance, validated_data):
        if "title" in validated_data:
            instance.title = validated_data["title"]
        if "summary" in validated_data:
            instance.summary = validated_data["summary"]
        if "from_laboratory" in validated_data:
            instance.from_laboratory = self._lab(validated_data["from_laboratory"])
        if "to_laboratory" in validated_data:
            instance.to_laboratory = self._lab(validated_data["to_laboratory"])
        if "linked_delivery_task" in validated_data:
            instance.linked_delivery_task = self._task(
                validated_data["linked_delivery_task"]
            )
        if "preferred_role" in validated_data:
            instance.preferred_role = validated_data["preferred_role"] or ""
        if "manifest_sha256" in validated_data:
            instance.manifest_sha256 = validated_data["manifest_sha256"]
        if "notes_limitations" in validated_data:
            instance.notes_limitations = validated_data["notes_limitations"]
        instance.save()
        return instance


class PackageTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Package.Status.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    to_laboratory = serializers.IntegerField(required=False, allow_null=True)


class IntakeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntakeRequest
        fields = (
            "id",
            "body",
            "contact",
            "status",
            "source",
            "package",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "package",
            "created_by",
            "created_at",
            "updated_at",
        )


class IntakeWriteSerializer(serializers.Serializer):
    body = serializers.CharField()
    contact = serializers.CharField(required=False, allow_blank=True, default="")
    source = serializers.ChoiceField(
        choices=IntakeRequest.Source.choices,
        required=False,
        default=IntakeRequest.Source.WEB_FORM,
    )

    def create(self, validated_data):
        return IntakeRequest.objects.create(
            workspace=self.context["workspace"],
            created_by=self.context["user"],
            body=validated_data["body"],
            contact=validated_data.get("contact", ""),
            source=validated_data.get("source", IntakeRequest.Source.WEB_FORM),
            status=IntakeRequest.Status.NEW,
        )


class IntakeTriageSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            IntakeRequest.Status.TRIAGED,
            IntakeRequest.Status.CLOSED,
        ]
    )


class IntakeConvertSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    summary = serializers.CharField(required=False, allow_blank=True, default="")
    from_laboratory = serializers.IntegerField(required=False, allow_null=True)
    to_laboratory = serializers.IntegerField(required=True)

    def validate_to_laboratory(self, value):
        if value is None:
            raise serializers.ValidationError("to_laboratory обязателен для convert.")
        return value


class PackageTransferSerializer(serializers.Serializer):
    to_laboratory = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")
