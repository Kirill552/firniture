import hashlib
import hmac
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import Response

log = logging.getLogger(__name__)

COOKIE_NAME = "ar_guest_draft"


def create_guest_draft_token(
    order_id: str,
    guest_session_id: str,
    secret: str,
    ttl_seconds: int = 604800,
) -> str:
    """Создать подписанный HMAC-SHA256 токен для анонимного черновика."""
    exp = int(datetime.now(UTC).timestamp()) + ttl_seconds
    payload = {
        "purpose": "guest_draft",
        "order_id": order_id,
        "guest_session_id": guest_session_id,
        "exp": exp,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"{body.hex()}.{signature}"


def verify_guest_draft_token(
    token: str,
    secret: str,
    expected_order_id: str | None = None,
    expected_guest_session_id: str | None = None,
) -> dict[str, Any] | None:
    """Проверить подпись, exp, purpose и привязку к order/session токена гостевого черновика."""
    if not token or "." not in token:
        return None
    try:
        body_hex, signature = token.split(".", 1)
        body = bytes.fromhex(body_hex)
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            log.warning("[GuestDraft] Signature mismatch")
            return None

        payload = json.loads(body)
        if not isinstance(payload, dict):
            return None

        if payload.get("purpose") != "guest_draft":
            log.warning("[GuestDraft] Invalid purpose")
            return None

        if expected_order_id is not None and payload.get("order_id") != expected_order_id:
            log.warning("[GuestDraft] Order ID mismatch")
            return None

        if (
            expected_guest_session_id is not None
            and payload.get("guest_session_id") != expected_guest_session_id
        ):
            log.warning("[GuestDraft] Guest session ID mismatch")
            return None

        exp = payload.get("exp")
        if not isinstance(exp, (int, float)):
            return None

        if datetime.now(UTC).timestamp() > exp:
            log.warning("[GuestDraft] Token expired")
            return None

        return payload
    except Exception as e:
        log.error(f"[GuestDraft] Verification failed: {e}")
        return None


def is_guest_draft_cookie_secure() -> bool:
    """Определить флаг Secure для гостевой cookie по окружению."""
    env = os.environ.get("APP_ENVIRONMENT", "dev").lower()
    return env in {"prod", "production"}


def set_guest_draft_cookie(
    response: Response,
    token: str,
    secure: bool | None = None,
    ttl_seconds: int = 604800,
) -> None:
    """Выставить HttpOnly-cookie с токеном черновика."""
    if secure is None:
        secure = is_guest_draft_cookie_secure()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=ttl_seconds,
        expires=ttl_seconds,
        path="/",
        domain=None,
        secure=secure,
        httponly=True,
        samesite="lax",
    )


def clear_guest_draft_cookie(response: Response, secure: bool | None = None) -> None:
    """Удалить HttpOnly-cookie с токеном черновика."""
    if secure is None:
        secure = is_guest_draft_cookie_secure()
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        domain=None,
        secure=secure,
        httponly=True,
        samesite="lax",
    )
