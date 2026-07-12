"""Проверки доступа к ресурсам фабрики — включая гостевые capability-токены.

Контракт:
- GuestIdentity / UserIdentity — иммутабельные идентичности
- resolve_guest_identity() — fail closed при отсутствии secret
- resolve_guest_identity_strict() — additionally rejects UUID-only fallback tokens
- enforce_access() — единая проверка для пользователей и гостей
- validate_guest_order_access() — order-bound guest access with scope + expiry
- claim_factory_access() — claim после логина (identity preservation)
- claim_guest_order_access() — claim with token validation (factory/order binding)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException

from api.guest_access import (
    GuestScope,
    decode_capability_token,
    has_scope,
    is_expired,
)

# ── UUID-only token guard ──────────────────────────────────────────

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_uuid_only_token(token_str: str) -> bool:
    """True если строка — bare UUID, а не подписанный capability-токен."""
    return bool(_UUID_RE.fullmatch(token_str.strip()))


# ── Идентичность ────────────────────────────────────────────────────


@dataclass(frozen=True)
class GuestIdentity:
    """Идентичность гостя из capability-токена."""

    factory_id: UUID
    scopes: list[GuestScope]
    token_id: str


@dataclass(frozen=True)
class UserIdentity:
    """Идентичность авторизованного пользователя."""

    factory_id: UUID
    user_id: UUID


Identity = GuestIdentity | UserIdentity


# ── Резолвинг гостевой идентичности ────────────────────────────────


def resolve_guest_identity(token_str: str | None, secret: str) -> GuestIdentity | None:
    """
    Извлечь гостевую идентичность из capability-токена.

    Fail closed: пустой/отсутствующий secret → None,
    невалидный или истёкший токен → None.
    """
    if not secret:
        # Secret обязателен — fail closed
        return None
    if not token_str:
        return None

    if is_expired(token_str, secret):
        return None

    token = decode_capability_token(token_str, secret)
    if token is None:
        return None

    return GuestIdentity(
        factory_id=token.factory_id,
        scopes=token.scopes,
        token_id=token.token_id,
    )


def resolve_guest_identity_strict(
    token_str: str | None,
    secret: str,
) -> GuestIdentity | None:
    """
    Жёсткий резолвинг: отвергает UUID-only fallback токены.

    Аналог resolve_guest_identity, но вызывает ValueError при обнаружении
    UUID-only токена — вызывающий код должен транслировать в 401.
    """
    if not secret:
        return None
    if not token_str:
        return None

    # Reject bare UUIDs that bypass HMAC signing
    if _is_uuid_only_token(token_str):
        raise ValueError("UUID-only token is not a valid capability token")

    if is_expired(token_str, secret):
        return None

    token = decode_capability_token(token_str, secret)
    if token is None:
        return None

    return GuestIdentity(
        factory_id=token.factory_id,
        scopes=token.scopes,
        token_id=token.token_id,
    )


def guest_has_scope(identity: GuestIdentity, required: GuestScope) -> bool:
    """Проверить scope у гостевой идентичности."""
    return has_scope(identity.scopes, required)


# ── Проверка доступа (расширение существующего API) ──────────────────


def has_factory_access(
    resource_factory_id: UUID | None,
    user_factory_id: UUID | None,
) -> bool:
    """
    Проверить доступ к ресурсу по фабрике.

    Правила:
    - resource_factory_id = None -> ресурс анонимный, доступен всем
    - resource_factory_id != None -> доступ только пользователю той же фабрики
    """
    if resource_factory_id is None:
        return True
    if user_factory_id is None:
        return False
    return resource_factory_id == user_factory_id


def enforce_factory_access(
    resource_factory_id: UUID | None,
    user_factory_id: UUID | None,
) -> None:
    """
    Бросает HTTPException при отсутствии доступа.

    401: нет авторизации для приватного ресурса.
    403: ресурс принадлежит другой фабрике.
    """
    if resource_factory_id is None:
        return

    if user_factory_id is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    if resource_factory_id != user_factory_id:
        raise HTTPException(status_code=403, detail="Нет доступа к ресурсу")


# ── Новый: расширенная проверка с поддержкой гостей ─────────────────


def enforce_access(
    resource_factory_id: UUID | None,
    identity: Identity | None,
    required_scope: GuestScope | None = None,
) -> None:
    """
    Универсальная проверка доступа для пользователей и гостей.

    Raises:
        HTTPException 401 — нет идентичности (анонимный запрос к приватному ресурсу)
        HTTPException 403 — нет доступа к фабрике или не хватает scope
    """
    if resource_factory_id is None:
        return  # Анонимный ресурс — доступен всем

    if identity is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    if identity.factory_id != resource_factory_id:
        raise HTTPException(status_code=403, detail="Нет доступа к ресурсу")

    # Scope-проверка только для гостей
    if required_scope is not None and isinstance(identity, GuestIdentity):
        if not guest_has_scope(identity, required_scope):
            raise HTTPException(
                status_code=403,
                detail=f"Недостаточно прав: требуется scope {required_scope.value}",
            )


def claim_factory_access(
    guest_factory_id: UUID,
    user_factory_id: UUID,
) -> None:
    """
    Claim после логина: проверить, что фабрика пользователя совпадает с фабрикой гостя.

    Raises:
        HTTPException 403 — фабрики не совпадают
    """
    if guest_factory_id != user_factory_id:
        raise HTTPException(
            status_code=403,
            detail="Фабрика гостевого токена не совпадает с фабрикой пользователя",
        )


# ── Order-bound guest access ──────────────────────────────────────


def validate_guest_order_access(
    token_str: str | None,
    secret: str,
    order_factory_id: UUID,
    required_scope: GuestScope = GuestScope.READ_ORDER,
) -> GuestIdentity:
    """
    Validate a guest capability token for access to a specific order.

    Enforces:
    - Secret must be non-empty (fail closed)
    - Token must be a signed capability token (not UUID-only)
    - Token must not be expired
    - Token's factory_id must match order's factory_id (tenant binding)
    - Token must carry the required scope

    Returns:
        GuestIdentity on success.

    Raises:
        HTTPException 401 — missing/invalid/expired token or UUID-only fallback
        HTTPException 403 — factory mismatch or insufficient scope
    """
    if not secret:
        raise HTTPException(
            status_code=401,
            detail="Guest capability secret not configured",
        )

    if not token_str:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    if _is_uuid_only_token(token_str):
        raise HTTPException(
            status_code=401,
            detail="UUID-only token is not a valid capability token",
        )

    token = decode_capability_token(token_str, secret)
    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid guest capability token",
        )

    # Check expiry after successful decode (is_expired returns True for unparseable tokens)
    if is_expired(token_str, secret):
        raise HTTPException(status_code=401, detail="Guest capability token expired")

    # Factory binding: token must be for the same factory as the order
    if token.factory_id != order_factory_id:
        raise HTTPException(
            status_code=403,
            detail="Guest token factory does not match order factory",
        )

    # Scope check
    if not has_scope(token.scopes, required_scope):
        raise HTTPException(
            status_code=403,
            detail=f"Недостаточно прав: требуется scope {required_scope.value}",
        )

    return GuestIdentity(
        factory_id=token.factory_id,
        scopes=token.scopes,
        token_id=token.token_id,
    )


def claim_guest_order_access(
    token_str: str | None,
    secret: str,
    user_factory_id: UUID,
) -> GuestIdentity:
    """
    Validate guest token during claim-after-login flow.

    After a guest logs in, they present their capability token to claim
    guest orders. This function:
    1. Validates the token (signed, not expired, not UUID-only)
    2. Verifies factory binding (token.factory_id == user_factory_id)

    Returns:
        GuestIdentity on success.

    Raises:
        HTTPException 401 — missing/invalid/expired token or UUID-only fallback
        HTTPException 403 — factory mismatch (cross-tenant claim denied)
    """
    if not secret:
        raise HTTPException(
            status_code=401,
            detail="Guest capability secret not configured",
        )

    if not token_str:
        raise HTTPException(status_code=401, detail="Guest capability token required for claim")

    if _is_uuid_only_token(token_str):
        raise HTTPException(
            status_code=401,
            detail="UUID-only token is not a valid capability token",
        )

    token = decode_capability_token(token_str, secret)
    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid guest capability token",
        )

    if is_expired(token_str, secret):
        raise HTTPException(status_code=401, detail="Guest capability token expired")

    # Factory binding for claim
    if token.factory_id != user_factory_id:
        raise HTTPException(
            status_code=403,
            detail="Guest token factory does not match user factory",
        )

    return GuestIdentity(
        factory_id=token.factory_id,
        scopes=token.scopes,
        token_id=token.token_id,
    )
