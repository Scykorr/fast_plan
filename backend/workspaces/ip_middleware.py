"""Optional workspace IP allowlist middleware (P7).

Runs after Django AuthenticationMiddleware and attempts JWT cookie auth so the
active workspace (and its allowlist) can be resolved for API requests.
"""

from __future__ import annotations

from django.http import JsonResponse

from accounts.security import client_ip, ip_allowed


class WorkspaceIpAllowlistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""
        if not path.startswith("/api/"):
            return self.get_response(request)
        if (
            path.startswith("/api/auth/")
            or path.startswith("/api/health")
            or path.startswith("/api/share/")
            or path.startswith("/api/crm/channels/telegram/")
        ):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            try:
                from accounts.authentication import CookieJWTAuthentication

                result = CookieJWTAuthentication().authenticate(request)
                if result is not None:
                    request.user, request.auth = result
                    user = request.user
            except Exception:  # noqa: BLE001
                return self.get_response(request)

        if user is None or not getattr(user, "is_authenticated", False):
            return self.get_response(request)

        from workspaces.services import get_request_workspace

        workspace = get_request_workspace(request)
        allowlist = getattr(workspace, "ip_allowlist", None) if workspace else None
        if not allowlist:
            return self.get_response(request)
        if ip_allowed(client_ip(request), allowlist):
            return self.get_response(request)
        return JsonResponse(
            {"detail": "IP address is not allowed for this workspace."},
            status=403,
        )
