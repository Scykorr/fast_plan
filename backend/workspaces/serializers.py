from rest_framework import serializers

from workspaces.webhooks import WEBHOOK_EVENTS
from workspaces.models import (
    WebhookDelivery,
    WebhookEndpoint,
    Workspace,
    WorkspaceAPIToken,
    WorkspaceInvitation,
    WorkspaceMember,
)


class WorkspaceSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    role = serializers.CharField()
    is_active = serializers.BooleanField()


class WorkspaceInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceInvitation
        fields = (
            "id",
            "email",
            "role",
            "token",
            "expires_at",
            "accepted_at",
            "created_at",
        )
        read_only_fields = ("id", "token", "expires_at", "accepted_at", "created_at")


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceMember
        fields = ("id", "user_id", "role", "joined_at")
        read_only_fields = ("id", "user_id", "joined_at")


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ("id", "name", "created_at")
        read_only_fields = fields


class WorkspaceAPITokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceAPIToken
        fields = (
            "id",
            "name",
            "prefix",
            "scopes",
            "created_at",
            "last_used_at",
            "expires_at",
            "revoked_at",
        )
        read_only_fields = fields


class WorkspaceAPITokenCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    scopes = serializers.ListField(
        child=serializers.ChoiceField(choices=("read", "write")),
        allow_empty=False,
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_scopes(self, value):
        return list(dict.fromkeys(value))


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = (
            "id",
            "name",
            "url",
            "events",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate_url(self, value):
        if not value.lower().startswith("https://"):
            raise serializers.ValidationError("Webhook URL must use HTTPS.")
        return value

    def validate_events(self, value):
        invalid = set(value) - WEBHOOK_EVENTS
        if invalid:
            raise serializers.ValidationError(
                f"Unsupported events: {', '.join(sorted(invalid))}"
            )
        if not value:
            raise serializers.ValidationError("Select at least one event.")
        return list(dict.fromkeys(value))


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = (
            "id",
            "event",
            "status_code",
            "error",
            "attempt_count",
            "delivered_at",
            "created_at",
        )
        read_only_fields = fields
