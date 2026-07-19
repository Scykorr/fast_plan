from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from django.conf import settings
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


def enforce_csrf(request):
    def dummy_get_response(_request):
        return None

    check = CSRFCheck(dummy_get_response)
    check.process_request(request)
    # DRF wraps APIView with csrf_exempt, so CsrfViewMiddleware marks
    # csrf_processing_done=True before authentication runs. Reset it so the
    # cookie-authenticated unsafe request is actually validated.
    request.csrf_processing_done = False
    reason = check.process_view(request, None, (), {})
    if reason:
        raise PermissionDenied(f"CSRF Failed: {reason}")


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate via Authorization header or HttpOnly access cookie.

    Cookie-authenticated unsafe methods require a valid CSRF token.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        raw_token = request.COOKIES.get(settings.JWT_ACCESS_COOKIE)
        if not raw_token:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            enforce_csrf(request)
        return user, validated_token


class WorkspaceAPITokenAuthentication(BaseAuthentication):
    keyword = b"bearer"

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != self.keyword:
            return None
        if len(parts) != 2:
            raise AuthenticationFailed("Invalid Authorization header.")
        try:
            raw_token = parts[1].decode()
        except UnicodeError as exc:
            raise AuthenticationFailed("Invalid API token.") from exc
        if not raw_token.startswith("fp_"):
            return None

        from workspaces.models import WorkspaceAPIToken

        candidates = WorkspaceAPIToken.objects.select_related(
            "created_by", "workspace"
        ).filter(prefix=raw_token[:12])
        token = next(
            (candidate for candidate in candidates if candidate.matches(raw_token)),
            None,
        )
        if token is None or not token.is_active:
            raise AuthenticationFailed("Invalid or expired API token.")
        required_scope = (
            "read"
            if request.method in ("GET", "HEAD", "OPTIONS", "TRACE")
            else "write"
        )
        if required_scope not in token.scopes:
            raise PermissionDenied(f"API token requires the '{required_scope}' scope.")
        if not token.workspace.memberships.filter(user=token.created_by).exists():
            raise AuthenticationFailed("API token owner is no longer a workspace member.")
        token.last_used_at = timezone.now()
        token.save(update_fields=["last_used_at"])
        return token.created_by, token

    def authenticate_header(self, request):
        return "Bearer"
