from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "username", "password", "first_name", "last_name")

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    active_workspace_id = serializers.IntegerField(
        source="active_workspace.id",
        read_only=True,
        allow_null=True,
    )
    active_workspace_name = serializers.CharField(
        source="active_workspace.name",
        read_only=True,
        allow_null=True,
    )
    avatar_url = serializers.SerializerMethodField()
    is_email_verified = serializers.BooleanField(read_only=True)

    def get_avatar_url(self, user):
        if not user.avatar:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(user.avatar.url) if request else user.avatar.url

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "avatar_url",
            "is_email_verified",
            "date_joined",
            "active_workspace_id",
            "active_workspace_name",
        )
        read_only_fields = fields


class ProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    is_email_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "avatar",
            "avatar_url",
            "is_email_verified",
        )
        read_only_fields = ("id", "email", "avatar_url", "is_email_verified")
        extra_kwargs = {
            "avatar": {"write_only": True, "required": False},
            "first_name": {"required": False},
            "last_name": {"required": False},
            "username": {"required": False},
        }

    def get_avatar_url(self, user):
        if not user.avatar:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(user.avatar.url) if request else user.avatar.url

    def validate_avatar(self, value):
        max_bytes = settings.AVATAR_MAX_BYTES
        if value.size > max_bytes:
            raise serializers.ValidationError(
                f"Аватар должен быть не больше {max_bytes // (1024 * 1024)} МБ."
            )
        return value

    def update(self, instance, validated_data):
        old_avatar = instance.avatar if "avatar" in validated_data else None
        instance = super().update(instance, validated_data)
        if old_avatar and old_avatar.name != instance.avatar.name:
            old_avatar.delete(save=False)
        return instance


class EmailVerificationSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()


class EmailVerificationResendSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordForgotSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value
