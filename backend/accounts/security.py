"""P7 security helpers: TOTP 2FA, auth sessions, IP allowlist."""

from __future__ import annotations

import hashlib
import ipaddress
import secrets
from typing import Iterable

import pyotp
from django.core.cache import cache
from django.utils import timezone

from accounts.models import AuthSession, User


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(user: User, secret: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(
        name=user.email, issuer_name="Fast Plan"
    )


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=1)


def hash_backup_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()


def generate_backup_codes(count: int = 8) -> list[str]:
    return [secrets.token_hex(4).upper() for _ in range(count)]


def consume_backup_code(user: User, code: str) -> bool:
    hashed = hash_backup_code(code)
    codes = list(user.totp_backup_codes or [])
    if hashed not in codes:
        return False
    codes.remove(hashed)
    user.totp_backup_codes = codes
    user.save(update_fields=["totp_backup_codes"])
    return True


def create_pre_auth_token(user_id: int, *, ttl: int = 300) -> str:
    token = secrets.token_urlsafe(32)
    cache.set(f"fp:2fa:preauth:{token}", user_id, ttl)
    return token


def consume_pre_auth_token(token: str) -> int | None:
    key = f"fp:2fa:preauth:{token}"
    user_id = cache.get(key)
    if user_id is None:
        return None
    cache.delete(key)
    return int(user_id)


def client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR") or ""
    if forwarded:
        return forwarded.split(",")[0].strip()
    return (request.META.get("REMOTE_ADDR") or "").strip()


def ip_allowed(client: str, allowlist: Iterable[str]) -> bool:
    entries = [item.strip() for item in allowlist if item and str(item).strip()]
    if not entries:
        return True
    if not client:
        return False
    try:
        addr = ipaddress.ip_address(client)
    except ValueError:
        return False
    for entry in entries:
        try:
            if "/" in entry:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return True
            elif addr == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue
    return False


def register_auth_session(user: User, refresh_token, *, request=None) -> AuthSession:
    jti = str(getattr(refresh_token, "get", lambda *_: None)("jti") or refresh_token.get("jti"))
    ua = ""
    ip = ""
    if request is not None:
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:400]
        ip = client_ip(request)[:64]
    session, _ = AuthSession.objects.update_or_create(
        user=user,
        refresh_jti=jti,
        defaults={
            "user_agent": ua,
            "ip_address": ip,
            "last_seen_at": timezone.now(),
            "revoked_at": None,
        },
    )
    return session


def touch_auth_session(refresh_jti: str, *, request=None) -> None:
    if not refresh_jti:
        return
    updates = {"last_seen_at": timezone.now()}
    if request is not None:
        updates["ip_address"] = client_ip(request)[:64]
        updates["user_agent"] = (request.META.get("HTTP_USER_AGENT") or "")[:400]
    AuthSession.objects.filter(refresh_jti=refresh_jti, revoked_at__isnull=True).update(
        **updates
    )


def revoke_auth_session(session: AuthSession) -> None:
    session.revoked_at = timezone.now()
    session.save(update_fields=["revoked_at"])
