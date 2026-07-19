from rest_framework import serializers

from workspaces.models import Workspace, WorkspaceInvitation, WorkspaceMember


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
