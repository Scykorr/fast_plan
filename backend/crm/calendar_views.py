"""CRM calendar API: in-app events + Google/Outlook OAuth sync."""

from __future__ import annotations

import secrets
import urllib.parse

from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.calendar_events import workspace_crm_events
from crm.calendar_sync import (
    GOOGLE_SCOPES,
    MS_SCOPES,
    _http_json,
    provider_configured,
    sync_connection,
)
from crm.models import CalendarConnection
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin


def _parse_year_month(request):
    try:
        year = int(request.query_params.get("year") or timezone.localdate().year)
        month = int(request.query_params.get("month") or timezone.localdate().month)
    except (TypeError, ValueError):
        year = timezone.localdate().year
        month = timezone.localdate().month
    return year, month


def _callback_url(request, provider: str) -> str:
    override = getattr(settings, "OAUTH_REDIRECT_BASE", "").strip()
    if override:
        return f"{override.rstrip('/')}/api/crm/calendar/oauth/{provider}/callback/"
    return request.build_absolute_uri(
        f"/api/crm/calendar/oauth/{provider}/callback/"
    )


def _frontend_settings() -> str:
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/settings?calendar_sync=1"


class CrmCalendarEventsView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        year, month = _parse_year_month(request)
        return Response(workspace_crm_events(self.get_workspace(), year, month))


class CalendarConnectionListView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        rows = CalendarConnection.objects.filter(
            workspace=self.get_workspace(), user=request.user
        )
        return Response(
            [
                {
                    "id": c.id,
                    "provider": c.provider,
                    "last_synced_at": c.last_synced_at,
                    "last_error": c.last_error,
                    "external_calendar_id": c.external_calendar_id,
                    "configured": bool(c.refresh_token),
                }
                for c in rows
            ]
        )


class CalendarProvidersView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        return Response(
            {
                "microsoft": provider_configured("microsoft"),
                "google": provider_configured("google"),
            }
        )


class CalendarOAuthStartView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, provider: str):
        if provider not in (
            CalendarConnection.Provider.MICROSOFT,
            CalendarConnection.Provider.GOOGLE,
        ):
            return HttpResponseBadRequest("Unknown provider")
        if not provider_configured(provider):
            return HttpResponseBadRequest("Calendar OAuth provider is not configured.")
        state = secrets.token_urlsafe(24)
        cache.set(
            f"fp:cal:oauth:{state}",
            {
                "provider": provider,
                "user_id": request.user.id,
                "workspace_id": self.get_workspace().id,
            },
            600,
        )
        if provider == CalendarConnection.Provider.MICROSOFT:
            params = {
                "client_id": settings.OAUTH_MICROSOFT_CLIENT_ID,
                "response_type": "code",
                "redirect_uri": _callback_url(request, provider),
                "response_mode": "query",
                "scope": MS_SCOPES,
                "state": state,
                "prompt": "consent",
            }
            uri = (
                "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
                + urllib.parse.urlencode(params)
            )
        else:
            params = {
                "client_id": settings.OAUTH_GOOGLE_CLIENT_ID,
                "response_type": "code",
                "redirect_uri": _callback_url(request, provider),
                "scope": GOOGLE_SCOPES,
                "state": state,
                "access_type": "offline",
                "prompt": "consent",
            }
            uri = (
                "https://accounts.google.com/o/oauth2/v2/auth?"
                + urllib.parse.urlencode(params)
            )
        return HttpResponseRedirect(uri)


class CalendarOAuthCallbackView(APIView):
    """Callback is unauthenticated; state cache binds user/workspace."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, provider: str):
        error = request.GET.get("error")
        if error:
            return HttpResponseRedirect(
                f"{_frontend_settings()}&cal_error={urllib.parse.quote(error)}"
            )
        state = request.GET.get("state") or ""
        payload = cache.get(f"fp:cal:oauth:{state}")
        cache.delete(f"fp:cal:oauth:{state}")
        if not payload or payload.get("provider") != provider:
            return HttpResponseRedirect(f"{_frontend_settings()}&cal_error=invalid_state")
        code = request.GET.get("code")
        if not code:
            return HttpResponseRedirect(f"{_frontend_settings()}&cal_error=missing_code")

        redirect_uri = _callback_url(request, provider)
        try:
            if provider == CalendarConnection.Provider.MICROSOFT:
                token = _http_json(
                    "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                    data={
                        "client_id": settings.OAUTH_MICROSOFT_CLIENT_ID,
                        "client_secret": settings.OAUTH_MICROSOFT_CLIENT_SECRET,
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                        "scope": MS_SCOPES,
                    },
                )
                scopes = MS_SCOPES
            else:
                token = _http_json(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.OAUTH_GOOGLE_CLIENT_ID,
                        "client_secret": settings.OAUTH_GOOGLE_CLIENT_SECRET,
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
                scopes = GOOGLE_SCOPES
        except Exception:  # noqa: BLE001
            return HttpResponseRedirect(
                f"{_frontend_settings()}&cal_error=token_exchange"
            )

        refresh = token.get("refresh_token") or ""
        access = token.get("access_token") or ""
        if not access:
            return HttpResponseRedirect(f"{_frontend_settings()}&cal_error=no_token")

        expires_in = int(token.get("expires_in") or 3600)
        connection, _ = CalendarConnection.objects.update_or_create(
            workspace_id=payload["workspace_id"],
            user_id=payload["user_id"],
            provider=provider,
            defaults={
                "refresh_token": refresh
                or CalendarConnection.objects.filter(
                    workspace_id=payload["workspace_id"],
                    user_id=payload["user_id"],
                    provider=provider,
                )
                .values_list("refresh_token", flat=True)
                .first()
                or "",
                "access_token": access,
                "token_expires_at": timezone.now() + timedelta(seconds=expires_in),
                "scopes": scopes,
                "last_error": "",
            },
        )
        if refresh:
            connection.refresh_token = refresh
            connection.save(update_fields=["refresh_token"])
        return HttpResponseRedirect(f"{_frontend_settings()}&cal_connected={provider}")


class CalendarConnectionSyncView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, pk):
        connection = CalendarConnection.objects.filter(
            workspace=self.get_workspace(), user=request.user, pk=pk
        ).first()
        if connection is None:
            return Response({"detail": "Not found"}, status=404)
        result = sync_connection(connection)
        status_code = 200 if result.get("ok") else 400
        return Response(result, status=status_code)


class CalendarConnectionDeleteView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def delete(self, request, pk):
        deleted, _ = CalendarConnection.objects.filter(
            workspace=self.get_workspace(), user=request.user, pk=pk
        ).delete()
        if not deleted:
            return Response({"detail": "Not found"}, status=404)
        return Response({"detail": "Disconnected"})
