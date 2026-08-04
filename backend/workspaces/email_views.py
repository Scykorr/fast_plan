"""Owner-only SMTP status and test-send (env-configured mail)."""

from __future__ import annotations

import time

from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import log_audit
from notifications.mail import send_app_email_result
from workspaces.mixins import WorkspaceMixin
from workspaces.views import _require_session_owner


def email_status_payload() -> dict:
    backend = settings.EMAIL_BACKEND or ""
    host = (settings.EMAIL_HOST or "").strip()
    user = (settings.EMAIL_HOST_USER or "").strip()
    is_console = "console" in backend.lower()
    is_locmem = "locmem" in backend.lower()
    configured = bool(host) and not is_console and not is_locmem
    return {
        "backend": backend,
        "host": host,
        "port": int(settings.EMAIL_PORT or 0),
        "use_tls": bool(settings.EMAIL_USE_TLS),
        "use_ssl": bool(settings.EMAIL_USE_SSL),
        "from_email": settings.DEFAULT_FROM_EMAIL or "",
        "host_user_set": bool(user),
        "require_email_verification": bool(
            getattr(settings, "REQUIRE_EMAIL_VERIFICATION", False)
        ),
        "is_console": is_console,
        "configured": configured,
        "go_live_ready": bool(
            configured
            and not is_console
            and not is_locmem
            and bool(user)
            and bool(getattr(settings, "DEFAULT_FROM_EMAIL", ""))
            and host.lower() not in ("localhost", "127.0.0.1", "")
        ),
    }


class WorkspaceEmailStatusView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        _require_session_owner(self, request, workspace)
        return Response(email_status_payload())


class WorkspaceEmailTestView(WorkspaceMixin, APIView):
    def post(self, request):
        workspace = self.get_workspace()
        _require_session_owner(self, request, workspace)

        raw_to = str(request.data.get("to") or "").strip()
        to = raw_to or (request.user.email or "").strip()
        if not to:
            raise ValidationError({"to": "Recipient email is required."})
        try:
            validate_email(to)
        except DjangoValidationError as exc:
            raise ValidationError({"to": "Enter a valid email address."}) from exc

        started = time.perf_counter()
        ok, detail = send_app_email_result(
            to=to,
            subject="Fast Plan — тест SMTP",
            template_base="email/smtp_test",
            context={
                "workspace_name": workspace.name,
                "recipient": to,
            },
        )
        latency_ms = int((time.perf_counter() - started) * 1000)

        log_audit(
            workspace,
            request.user,
            "email.test",
            "Email",
            None,
            summary=f"SMTP test to {to}: {'ok' if ok else 'failed'}",
            changes={"ok": ok, "to": to},
        )

        return Response(
            {
                "ok": ok,
                "detail": detail,
                "to": to,
                "latency_ms": latency_ms,
                "status": email_status_payload(),
            }
        )
