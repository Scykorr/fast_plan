from django.conf import settings
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied
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
