"""P7 SSO: Google / Microsoft OAuth2 authorization-code flow."""

from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.cookies import set_auth_cookies
from accounts.models import SocialAccount, User
from accounts.security import create_pre_auth_token, register_auth_session

# Google IdP temporarily disabled (re-enable by removing from this set).
DISABLED_PROVIDERS = frozenset({"google"})

PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
        "client_id_setting": "OAUTH_GOOGLE_CLIENT_ID",
        "client_secret_setting": "OAUTH_GOOGLE_CLIENT_SECRET",
    },
    "microsoft": {
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/oidc/userinfo",
        "scope": "openid email profile User.Read",
        "client_id_setting": "OAUTH_MICROSOFT_CLIENT_ID",
        "client_secret_setting": "OAUTH_MICROSOFT_CLIENT_SECRET",
    },
}


def _provider_config(provider: str) -> dict | None:
    if provider in DISABLED_PROVIDERS:
        return None
    meta = PROVIDERS.get(provider)
    if meta is None:
        return None
    client_id = getattr(settings, meta["client_id_setting"], "").strip()
    client_secret = getattr(settings, meta["client_secret_setting"], "").strip()
    if not client_id or not client_secret:
        return None
    return {**meta, "client_id": client_id, "client_secret": client_secret}


def _callback_url(request, provider: str) -> str:
    override = getattr(settings, "OAUTH_REDIRECT_BASE", "").strip()
    if override:
        return f"{override.rstrip('/')}/api/auth/oauth/{provider}/callback/"
    return request.build_absolute_uri(f"/api/auth/oauth/{provider}/callback/")


def _frontend_redirect(next_path: str = "/") -> str:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    path = next_path if next_path.startswith("/") else f"/{next_path}"
    return f"{base}{path}"


def _unique_username(base: str) -> str:
    candidate = slugify(base)[:40] or "user"
    username = candidate
    n = 1
    while User.objects.filter(username=username).exists():
        username = f"{candidate}{n}"
        n += 1
    return username


def _http_json(url: str, *, data: dict | None = None, headers: dict | None = None):
    body = None
    req_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        req_headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=req_headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 — fixed IdP URLs
        return json.loads(resp.read().decode("utf-8"))


def _resolve_user(*, provider: str, uid: str, email: str, profile: dict) -> User:
    link = (
        SocialAccount.objects.filter(provider=provider, uid=uid)
        .select_related("user")
        .first()
    )
    if link is not None:
        return link.user

    user = None
    if email:
        user = User.objects.filter(email__iexact=email).first()
    if user is None:
        local = (email or f"{provider}.{uid}").split("@")[0]
        user = User(
            email=email or f"{provider}_{uid}@users.noreply.local",
            username=_unique_username(local),
            first_name=(profile.get("given_name") or profile.get("givenName") or "")[
                :150
            ],
            last_name=(profile.get("family_name") or profile.get("surname") or "")[
                :150
            ],
        )
        user.set_unusable_password()
        user.email_verified_at = timezone.now()
        user.save()
    elif user.email_verified_at is None and email:
        user.verify_email()

    SocialAccount.objects.update_or_create(
        provider=provider,
        uid=uid,
        defaults={
            "user": user,
            "email": email or "",
            "extra_data": {
                k: profile.get(k)
                for k in ("name", "picture", "locale")
                if profile.get(k) is not None
            },
        },
    )
    return user


def _issue_login_response(request, user: User, *, next_path: str = "/"):
    if user.is_totp_enabled:
        token = create_pre_auth_token(user.id)
        q = urllib.parse.urlencode(
            {
                "oauth_2fa": "1",
                "pre_auth_token": token,
                "next": next_path,
            }
        )
        return HttpResponseRedirect(_frontend_redirect(f"/login?{q}"))

    refresh = RefreshToken.for_user(user)
    register_auth_session(user, refresh, request=request)
    response = HttpResponseRedirect(_frontend_redirect(next_path))
    set_auth_cookies(response, access=str(refresh.access_token), refresh=str(refresh))
    return response


class OAuthProvidersView(APIView):
    """List which IdPs are configured (for UI buttons)."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "google": _provider_config("google") is not None,
                "microsoft": _provider_config("microsoft") is not None,
            }
        )


class OAuthStartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, provider: str):
        cfg = _provider_config(provider)
        if cfg is None:
            return HttpResponseBadRequest("OAuth provider is not configured.")
        next_path = request.GET.get("next") or "/"
        state = secrets.token_urlsafe(24)
        cache.set(
            f"fp:oauth:state:{state}",
            {"provider": provider, "next": next_path},
            600,
        )
        params = {
            "client_id": cfg["client_id"],
            "redirect_uri": _callback_url(request, provider),
            "response_type": "code",
            "scope": cfg["scope"],
            "state": state,
            "prompt": "select_account",
        }
        if provider == "google":
            params["access_type"] = "offline"
        uri = f"{cfg['authorize_url']}?{urllib.parse.urlencode(params)}"
        return HttpResponseRedirect(uri)


class OAuthCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, provider: str):
        cfg = _provider_config(provider)
        if cfg is None:
            return HttpResponseBadRequest("OAuth provider is not configured.")
        error = request.GET.get("error")
        if error:
            return HttpResponseRedirect(
                _frontend_redirect(f"/login?oauth_error={urllib.parse.quote(error)}")
            )
        state = request.GET.get("state") or ""
        payload = cache.get(f"fp:oauth:state:{state}")
        cache.delete(f"fp:oauth:state:{state}")
        if not payload or payload.get("provider") != provider:
            return HttpResponseRedirect(
                _frontend_redirect("/login?oauth_error=invalid_state")
            )
        code = request.GET.get("code")
        if not code:
            return HttpResponseRedirect(
                _frontend_redirect("/login?oauth_error=missing_code")
            )
        try:
            token = _http_json(
                cfg["token_url"],
                data={
                    "client_id": cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": _callback_url(request, provider),
                },
            )
            access = token.get("access_token")
            if not access:
                raise ValueError("no access_token")
            profile = _http_json(
                cfg["userinfo_url"],
                headers={"Authorization": f"Bearer {access}"},
            )
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, json.JSONDecodeError):
            return HttpResponseRedirect(
                _frontend_redirect("/login?oauth_error=token_exchange")
            )

        uid = str(profile.get("sub") or profile.get("id") or "").strip()
        email = (profile.get("email") or "").strip().lower()
        if not uid:
            return HttpResponseRedirect(
                _frontend_redirect("/login?oauth_error=no_subject")
            )
        user = _resolve_user(
            provider=provider, uid=uid, email=email, profile=profile
        )
        return _issue_login_response(
            request, user, next_path=payload.get("next") or "/"
        )
