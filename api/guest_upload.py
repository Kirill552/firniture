"""Защита публичной загрузки: identity, Redis gates и одноразовые grants."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
from fastapi import Request, Response

from api.settings import settings

log = logging.getLogger(__name__)

GUEST_SESSION_COOKIE = "ar_guest_session"
GUEST_SESSION_TTL = 86400 * 7
GUEST_BURST_KEY = "guest-upload:burst:{ident}"
GUEST_DAILY_KEY = "guest-upload:daily:{ident}"
GUEST_LOCK_KEY = "guest-upload:lock:{ident}"
GUEST_GRANT_KEY = "guest-upload:grant:{nonce}"

_RATE_LIMIT_SCRIPT = """
local burst_key = KEYS[1]
local daily_key = KEYS[2]
local now = tonumber(ARGV[1])
local member = ARGV[2]
local burst_window = tonumber(ARGV[3])
local burst_limit = tonumber(ARGV[4])
local daily_window = tonumber(ARGV[5])
local daily_limit = tonumber(ARGV[6])
redis.call('ZREMRANGEBYSCORE', burst_key, '-inf', now - burst_window)
redis.call('ZREMRANGEBYSCORE', daily_key, '-inf', now - daily_window)
if redis.call('ZCARD', burst_key) >= burst_limit then
  local oldest = redis.call('ZRANGE', burst_key, 0, 0, 'WITHSCORES')
  local score = oldest[2] and tonumber(oldest[2]) or now
  return {0, math.max(1, math.floor(burst_window - (now - score)))}
end
if redis.call('ZCARD', daily_key) >= daily_limit then
  local oldest = redis.call('ZRANGE', daily_key, 0, 0, 'WITHSCORES')
  local score = oldest[2] and tonumber(oldest[2]) or now
  return {0, math.max(1, math.floor(daily_window - (now - score)))}
end
redis.call('ZADD', burst_key, now, member)
redis.call('EXPIRE', burst_key, burst_window)
redis.call('ZADD', daily_key, now, member)
redis.call('EXPIRE', daily_key, daily_window)
return {1, 0}
"""

_COMPARE_DELETE_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""


@dataclass(frozen=True)
class GuestIdentity:
    identity_hash: str
    ip: str
    session_id: str
    ip_hash: str | None = None


def _get_secret() -> str:
    secret = settings.GUEST_UPLOAD_SECRET or ""
    if len(secret) < 32:
        raise RuntimeError("GUEST_UPLOAD_SECRET должен содержать не менее 32 символов")
    return secret


def _hmac(data: str, secret: str) -> str:
    return hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()


def _hash_file_for_grant(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def get_trusted_client_ip(request: Request) -> str:
    peer = request.client.host if request.client and request.client.host else "unknown"
    cidrs = [value.strip() for value in settings.TRUSTED_PROXY_CIDRS.split(",") if value.strip()]
    try:
        peer_ip = ipaddress.ip_address(peer)
        trusted = any(peer_ip in ipaddress.ip_network(cidr, strict=False) for cidr in cidrs)
    except ValueError:
        trusted = False
    if not trusted:
        return peer

    forwarded = request.headers.get("x-forwarded-for", "")
    parts = [value.strip() for value in forwarded.split(",") if value.strip()]
    if len(parts) != 1:
        return peer
    try:
        return str(ipaddress.ip_address(parts[0]))
    except ValueError:
        return peer


def get_or_create_guest_session(request: Request, response: Response | None = None) -> str:
    session_id = request.cookies.get(GUEST_SESSION_COOKIE)
    if not session_id or len(session_id) < 16:
        session_id = secrets.token_urlsafe(24)
        if response is not None:
            response.set_cookie(
                GUEST_SESSION_COOKIE,
                session_id,
                max_age=GUEST_SESSION_TTL,
                httponly=True,
                secure=True,
                samesite="lax",
            )
    return session_id


def resolve_guest_identity(request: Request, response: Response | None = None) -> GuestIdentity:
    secret = _get_secret()
    ip = get_trusted_client_ip(request)
    session_id = get_or_create_guest_session(request, response)
    return GuestIdentity(
        _hmac(f"{ip}|{session_id}", secret),
        ip,
        session_id,
        _hmac(f"ip|{ip}", secret),
    )


async def _redis_client() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)  # type: ignore[arg-type]


async def check_guest_rate_limits(ident: GuestIdentity) -> tuple[bool, int | None, str | None]:
    """Атомарно проверить и учесть каждую попытку до обработки файла."""
    try:
        redis = await _redis_client()

        async def consume(bucket_identity: str) -> tuple[bool, int | None, str | None]:
            now = time.time()
            result = await redis.eval(
                _RATE_LIMIT_SCRIPT,
                2,
                GUEST_BURST_KEY.format(ident=bucket_identity),
                GUEST_DAILY_KEY.format(ident=bucket_identity),
                now,
                f"{now}:{secrets.token_hex(8)}",
                settings.GUEST_UPLOAD_BURST_WINDOW_SECONDS,
                settings.GUEST_UPLOAD_BURST_LIMIT,
                settings.GUEST_UPLOAD_DAILY_WINDOW_SECONDS,
                settings.GUEST_UPLOAD_DAILY_LIMIT,
            )
            if bool(int(result[0])):
                return True, None, None
            return False, max(1, int(result[1])), "rate_limited"

        # Отдельный лимит по IP нельзя обойти очисткой cookie сессии.
        if ident.ip_hash:
            ip_result = await consume(ident.ip_hash)
            if not ip_result[0]:
                return ip_result
        return await consume(ident.identity_hash)
    except Exception as exc:
        log.error("Redis недоступен для guest rate limit: %s", exc)
        return False, None, "service_unavailable"


async def record_guest_upload_attempt(_ident: GuestIdentity) -> None:
    """Совместимость: попытка уже атомарно учтена в check_guest_rate_limits."""


async def acquire_analysis_lock(ident: GuestIdentity) -> str | None:
    token = secrets.token_urlsafe(18)
    try:
        redis = await _redis_client()
        acquired = await redis.set(
            GUEST_LOCK_KEY.format(ident=ident.identity_hash),
            token,
            ex=settings.GUEST_UPLOAD_CONCURRENCY_TTL,
            nx=True,
        )
        return token if acquired else None
    except Exception as exc:
        log.error("Redis недоступен для guest lock: %s", exc)
        return None


async def release_analysis_lock(ident: GuestIdentity, token: str) -> None:
    try:
        redis = await _redis_client()
        await redis.eval(
            _COMPARE_DELETE_SCRIPT,
            1,
            GUEST_LOCK_KEY.format(ident=ident.identity_hash),
            token,
        )
    except Exception as exc:
        log.warning("Не удалось освободить guest lock: %s", exc)


def _sign_grant(payload: dict[str, Any], secret: str) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"{body.hex()}.{signature}"


def _verify_grant(token: str, secret: str) -> dict[str, Any] | None:
    try:
        body_hex, signature = token.rsplit(".", 1)
        body = bytes.fromhex(body_hex)
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None
        payload = json.loads(body)
        return payload if isinstance(payload, dict) else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


async def issue_guest_upload_grant(file_bytes: bytes, ident: GuestIdentity | None = None) -> str:
    secret = _get_secret()
    nonce = secrets.token_urlsafe(18)
    file_hash = _hash_file_for_grant(file_bytes)
    payload = {
        "scope": "create_anonymous_order",
        "nonce": nonce,
        "file_hash": file_hash,
        "exp": (datetime.now(UTC) + timedelta(seconds=settings.GUEST_GRANT_TTL_SECONDS)).isoformat(),
        "iat": datetime.now(UTC).isoformat(),
    }
    if ident is not None:
        payload["identity_hash"] = ident.identity_hash
    redis = await _redis_client()
    stored = await redis.set(
        GUEST_GRANT_KEY.format(nonce=nonce),
        file_hash,
        ex=settings.GUEST_GRANT_TTL_SECONDS,
        nx=True,
    )
    if not stored:
        raise RuntimeError("Не удалось сохранить nonce guest grant")
    return _sign_grant(payload, secret)


async def validate_and_consume_grant(grant_token: str) -> bool:
    try:
        payload = _verify_grant(grant_token, _get_secret())
        if not payload or payload.get("scope") != "create_anonymous_order":
            return False
        expires_at = datetime.fromisoformat(str(payload["exp"]).replace("Z", "+00:00"))
        if datetime.now(UTC) >= expires_at:
            return False
        nonce = str(payload["nonce"])
        expected_hash = str(payload["file_hash"])
        redis = await _redis_client()
        consumed = await redis.eval(
            _COMPARE_DELETE_SCRIPT,
            1,
            GUEST_GRANT_KEY.format(nonce=nonce),
            expected_hash,
        )
        return bool(int(consumed))
    except Exception as exc:
        log.error("Не удалось проверить guest grant: %s", exc)
        return False


async def is_grant_already_used(grant_token: str) -> bool:
    payload = _verify_grant(grant_token, _get_secret())
    if not payload or not payload.get("nonce"):
        return True
    try:
        redis = await _redis_client()
        return await redis.get(GUEST_GRANT_KEY.format(nonce=payload["nonce"])) is None
    except Exception:
        return True
