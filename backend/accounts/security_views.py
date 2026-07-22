"""P7 security API: 2FA, sessions, workspace IP allowlist."""

from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.cookies import set_auth_cookies
from accounts.models import AuthSession, User
from accounts.security import (
    consume_backup_code,
    consume_pre_auth_token,
    generate_backup_codes,
    generate_totp_secret,
    hash_backup_code,
    register_auth_session,
    totp_provisioning_uri,
    verify_totp,
)
from accounts.serializers import UserSerializer
from workspaces.mixins import IsWorkspaceOwner, WorkspaceMixin


class TwoFactorSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.is_totp_enabled:
            raise ValidationError({"detail": "2FA already enabled."})
        secret = generate_totp_secret()
        request.user.totp_secret = secret
        request.user.totp_enabled_at = None
        request.user.save(update_fields=["totp_secret", "totp_enabled_at"])
        return Response(
            {
                "secret": secret,
                "otpauth_url": totp_provisioning_uri(request.user, secret),
            }
        )


class TwoFactorEnableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = str(request.data.get("code") or "").strip()
        secret = request.user.totp_secret
        if not secret:
            raise ValidationError({"detail": "Call setup first."})
        if request.user.is_totp_enabled:
            raise ValidationError({"detail": "2FA already enabled."})
        if not verify_totp(secret, code):
            raise ValidationError({"code": "Invalid code."})
        raw_codes = generate_backup_codes()
        request.user.totp_enabled_at = timezone.now()
        request.user.totp_backup_codes = [hash_backup_code(c) for c in raw_codes]
        request.user.save(
            update_fields=["totp_enabled_at", "totp_backup_codes"]
        )
        return Response(
            {
                "detail": "2FA enabled",
                "backup_codes": raw_codes,
                "user": UserSerializer(request.user, context={"request": request}).data,
            }
        )


class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = str(request.data.get("code") or "").strip()
        password = request.data.get("password") or ""
        if not request.user.check_password(password):
            raise ValidationError({"password": "Invalid password."})
        if request.user.is_totp_enabled:
            ok = verify_totp(request.user.totp_secret, code) or consume_backup_code(
                request.user, code
            )
            if not ok:
                raise ValidationError({"code": "Invalid code."})
        request.user.totp_secret = ""
        request.user.totp_enabled_at = None
        request.user.totp_backup_codes = []
        request.user.save(
            update_fields=["totp_secret", "totp_enabled_at", "totp_backup_codes"]
        )
        return Response(
            {
                "detail": "2FA disabled",
                "user": UserSerializer(request.user, context={"request": request}).data,
            }
        )


class TwoFactorVerifyView(APIView):
    """Complete login after password step when 2FA is required."""

    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("pre_auth_token") or ""
        code = str(request.data.get("code") or "").strip()
        user_id = consume_pre_auth_token(token)
        if user_id is None:
            raise ValidationError({"pre_auth_token": "Invalid or expired."})
        user = User.objects.filter(pk=user_id).first()
        if user is None or not user.is_totp_enabled:
            raise ValidationError({"detail": "2FA not available."})
        ok = verify_totp(user.totp_secret, code) or consume_backup_code(user, code)
        if not ok:
            raise ValidationError({"code": "Invalid code."})
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        register_auth_session(user, refresh, request=request)
        response = Response(
            {
                "detail": "ok",
                "user": UserSerializer(user, context={"request": request}).data,
            }
        )
        set_auth_cookies(response, access=access, refresh=str(refresh))
        return response


class AuthSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        current_jti = ""
        from django.conf import settings
        from rest_framework_simplejwt.tokens import UntypedToken

        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if raw:
            try:
                current_jti = str(UntypedToken(raw).get("jti") or "")
            except TokenError:
                current_jti = ""
        rows = AuthSession.objects.filter(user=request.user, revoked_at__isnull=True)[
            :50
        ]
        return Response(
            [
                {
                    "id": row.id,
                    "user_agent": row.user_agent,
                    "ip_address": row.ip_address,
                    "created_at": row.created_at,
                    "last_seen_at": row.last_seen_at,
                    "is_current": bool(current_jti) and row.refresh_jti == current_jti,
                }
                for row in rows
            ]
        )


class AuthSessionRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = AuthSession.objects.filter(
            user=request.user, pk=session_id, revoked_at__isnull=True
        ).first()
        if session is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at"])
        try:
            from rest_framework_simplejwt.token_blacklist.models import (
                BlacklistedToken,
                OutstandingToken,
            )

            outstanding = OutstandingToken.objects.filter(
                jti=session.refresh_jti
            ).first()
            if outstanding is not None:
                BlacklistedToken.objects.get_or_create(token=outstanding)
        except Exception:  # noqa: BLE001
            pass
        return Response({"detail": "revoked"})


class AuthSessionRevokeOthersView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.conf import settings
        from rest_framework_simplejwt.tokens import UntypedToken

        current_jti = ""
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if raw:
            try:
                current_jti = str(UntypedToken(raw).get("jti") or "")
            except TokenError:
                current_jti = ""
        qs = AuthSession.objects.filter(user=request.user, revoked_at__isnull=True)
        if current_jti:
            qs = qs.exclude(refresh_jti=current_jti)
        jtis = list(qs.values_list("refresh_jti", flat=True))
        updated = qs.update(revoked_at=timezone.now())
        if jtis:
            try:
                from rest_framework_simplejwt.token_blacklist.models import (
                    BlacklistedToken,
                    OutstandingToken,
                )

                for outstanding in OutstandingToken.objects.filter(jti__in=jtis):
                    BlacklistedToken.objects.get_or_create(token=outstanding)
            except Exception:  # noqa: BLE001
                pass
        return Response({"revoked": updated})


class WorkspaceIpAllowlistView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceOwner]

    def get(self, request):
        workspace = self.get_workspace()
        return Response({"ip_allowlist": workspace.ip_allowlist or []})

    def patch(self, request):
        workspace = self.get_workspace()
        raw = request.data.get("ip_allowlist")
        if raw is None:
            raise ValidationError({"ip_allowlist": "Required."})
        if not isinstance(raw, list):
            raise ValidationError({"ip_allowlist": "Must be a list of IPs/CIDRs."})
        cleaned = [str(item).strip() for item in raw if str(item).strip()]
        workspace.ip_allowlist = cleaned
        workspace.save(update_fields=["ip_allowlist"])
        return Response({"ip_allowlist": workspace.ip_allowlist})
