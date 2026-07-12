"""Гостевой capability-токен: подписанное ограничение доступа к фабрике.

Контракт:
- Токен = base64url(payload).base64url(signature)
- payload: {"factory_id": str, "scopes": [str], "expires_at": str, "iat": str, "jti": str}
- signature: HMAC-SHA256(payload_bytes, secret)
- Секрет НЕ хардкодится — передаётся через settings.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

# ── Scopes ──────────────────────────────────────────────────────────

class GuestScope(str, Enum):
    """Области доступа для гостевого токена."""
    READ_ORDER = "read:order"
    READ_BOM = "read:bom"
    WILDCARD = "*"


# ── Модель payload ──────────────────────────────────────────────────

class CapabilityToken:
    """Декодированный гостевой capability-токен."""

    __slots__ = ("factory_id", "scopes", "expires_at", "issued_at", "token_id")

    def __init__(
        self,
        factory_id: UUID,
        scopes: list[GuestScope],
        expires_at: str,
        issued_at: str | None = None,
        token_id: str | None = None,
    ) -> None:
        self.factory_id = factory_id
        self.scopes = scopes
        self.expires_at = expires_at
        self.issued_at = issued_at or datetime.now(UTC).isoformat()
        self.token_id = token_id or ""


# ── Вспомогательные ────────────────────────────────────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def _payload_to_dict(token: CapabilityToken) -> dict:
    return {
        "factory_id": str(token.factory_id),
        "scopes": [s.value for s in token.scopes],
        "expires_at": token.expires_at,
        "iat": token.issued_at,
        "jti": token.token_id,
    }


def _dict_to_payload(d: dict) -> CapabilityToken:
    return CapabilityToken(
        factory_id=UUID(d["factory_id"]),
        scopes=[GuestScope(s) for s in d["scopes"]],
        expires_at=d["expires_at"],
        issued_at=d.get("iat", ""),
        token_id=d.get("jti", ""),
    )


# ── Публичный API ──────────────────────────────────────────────────

def encode_capability_token(token: CapabilityToken, secret: str) -> str:
    """
    Закодировать capability-токен.

    Формат: base64url(json_payload).base64url(hmac_sha256)
    """
    payload_dict = _payload_to_dict(token)
    payload_bytes = json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    return _b64url_encode(payload_bytes) + "." + _b64url_encode(signature)


def decode_capability_token(token_str: str, secret: str) -> CapabilityToken | None:
    """
    Декодировать и проверить подпись capability-токена.

    Returns:
        CapabilityToken если валиден, иначе None.
    """
    if not token_str or "." not in token_str:
        return None

    try:
        body_b64, sig_b64 = token_str.rsplit(".", 1)
        payload_bytes = _b64url_decode(body_b64)
        expected_sig = hmac.new(
            secret.encode("utf-8"), payload_bytes, hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_dict = json.loads(payload_bytes)
        return _dict_to_payload(payload_dict)
    except Exception:
        return None


def is_expired(token_str: str, secret: str) -> bool:
    """Проверить, истёк ли токен (сравнивает expires_at с текущим временем)."""
    token = decode_capability_token(token_str, secret)
    if token is None:
        return True

    try:
        expires = datetime.fromisoformat(token.expires_at.replace("Z", "+00:00"))
        return datetime.now(UTC) >= expires
    except (ValueError, TypeError):
        return True


def has_scope(scopes: list[GuestScope], required: GuestScope) -> bool:
    """Проверить, есть ли required scope в списке (учитывает wildcard)."""
    if GuestScope.WILDCARD in scopes:
        return True
    return required in scopes


def extract_factory_id_from_token(token_str: str) -> UUID | None:
    """Извлечь factory_id из токена (без полной проверки подписи — для логирования)."""
    try:
        body_b64 = token_str.rsplit(".", 1)[0]
        payload_bytes = _b64url_decode(body_b64)
        payload_dict = json.loads(payload_bytes)
        return UUID(payload_dict["factory_id"])
    except Exception:
        return None
