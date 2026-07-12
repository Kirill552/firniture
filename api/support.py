"""Support incident contact core — typed payloads, redaction, response contract.

Приём обращений в поддержку с валидацией, автоматической очисткой
описаний от секретов/промптов/изображений и структурированным
ответом. Не выполняет отправку email / вызов внешних сервисов —
интеграция с провайдерами отложена (см. TODO: route/UI/legal).

Redaction policy:
- Email addresses → ``[REDACTED_EMAIL]``
- Phone numbers (RU/intl) → ``[REDACTED_PHONE]``
- API keys / tokens (``sk-…``, ``Bearer …``) → ``[REDACTED_SECRET]``
- Base64 data-URIs (``data:image/…``) → ``[REDACTED_IMAGE]``
- AI prompt wrappers (``<<SYS>>…<</SYS>>``) → ``[REDACTED_PROMPT]``
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ── Categories ─────────────────────────────────────────────────────

class SupportCategory(str, Enum):
    """Тип обращения."""

    ORDER_ISSUE = "order_issue"          # Проблема с заказом
    BILLING = "billing"                  # Вопросы по оплате
    TECHNICAL = "technical"              # Техническая проблема
    FEATURE_REQUEST = "feature_request"  # Запрос на функционал
    OTHER = "other"                      # Прочее


# ── Redaction patterns ────────────────────────────────────────────

# Base64 data-URIs (capture everything from ``data:image`` to end)
_RE_DATA_URI = re.compile(
    r"data:image/[a-zA-Z]+;base64,[A-Za-z0-9+/=\s]+",
    re.IGNORECASE,
)

# API keys / Bearer tokens
_RE_API_KEY = re.compile(
    r"(?:"
    r"sk-[A-Za-z0-9_-]{8,}"              # OpenAI / common prefix
    r"|Bearer\s+[A-Za-z0-9._-]{8,}"      # Bearer tokens
    r"|AKIA[A-Z0-9]{16}"                 # AWS access keys
    r"|xoxb-[A-Za-z0-9-]+"               # Slack bot tokens
    r")",
    re.IGNORECASE,
)

# Email addresses
_RE_EMAIL = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
)

# Phone numbers (RU: +7…, intl: +…, local 8…)
_RE_PHONE = re.compile(
    r"(?:"
    r"\+7[\s\-()0-9]{10,}"               # RU mobile
    r"|\+[\d][\s\-()0-9]{8,}"            # International
    r"|8[\s\-()0-9]{10,}"                # RU local
    r")",
)

# AI prompt wrappers
_RE_PROMPT = re.compile(
    r"<<SYS>>.*?<</SYS>>",
    re.DOTALL | re.IGNORECASE,
)


def redact_description(text: str) -> str:
    """Скрывает секреты, промпты и изображения в тексте обращения.

    Не изменяет длину текста для целей валидации — замены идентичны
    по семантике ``[REDACTED_*]``.
    """
    result = _RE_DATA_URI.sub("[REDACTED_IMAGE]", text)
    result = _RE_API_KEY.sub("[REDACTED_SECRET]", result)
    result = _RE_PROMPT.sub("[REDACTED_PROMPT]", result)
    result = _RE_EMAIL.sub("[REDACTED_EMAIL]", result)
    result = _RE_PHONE.sub("[REDACTED_PHONE]", result)
    return result


# ── Request / Response contracts ───────────────────────────────────

class SupportIncidentRequest(BaseModel):
    """Payload обращения в поддержку.

    ``order_id`` и ``artifact_id`` — опциональны; хотя бы одно
    должно быть задано.  Описание проходит автоматическую
    redaction перед сохранением.
    """

    order_id: uuid.UUID | None = None
    artifact_id: uuid.UUID | None = None
    category: SupportCategory
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Описание проблемы (автоматическая redaction секретов/изображений)",
    )
    contact_name: str | None = Field(
        None,
        max_length=200,
        description="Имя обратившегося",
    )
    contact_email: str = Field(
        ...,
        max_length=254,
        description="Email для обратной связи",
    )

    @field_validator("contact_email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Некорректный email")
        return v

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: str) -> str:
        return v.strip()

    model_config = ConfigDict(
        str_strip_whitespace=True,
        frozen=True,
    )


class SupportIncidentResponse(BaseModel):
    """Структурированный ответ на обращение.

    Не содержит тела обращения — только мета-данные для
    трекинга и фронтенда. Интеграция с провайдером email
    отложена (TODO: route/UI/legal).
    """

    incident_id: str = Field(
        ...,
        description="Уникальный идентификатор обращения",
    )
    status: Literal["received", "pending", "rejected"] = "received"
    category: SupportCategory
    redacted_description: str = Field(
        ...,
        description="Описание после автоматической redaction",
    )
    created_at: datetime

    model_config = ConfigDict(frozen=True)


# ── Core logic (no I/O) ───────────────────────────────────────────

class SupportIncidentError(Exception):
    """Ошибка валидации обращения."""


def create_support_incident(
    request: SupportIncidentRequest,
) -> SupportIncidentResponse:
    """Обработать обращение и вернуть структурированный ответ.

    Выполняет:
    1. Валидацию ``order_id`` / ``artifact_id`` (хотя бы одно).
    2. Redaction описания.
    3. Генерацию ``incident_id`` и ``created_at``.

    Не выполняет:
    - Отправку email
    - Сохранение в БД
    - Вызов внешних сервисов
    """
    if request.order_id is None and request.artifact_id is None:
        raise SupportIncidentError(
            "Требуется хотя бы один идентификатор: order_id или artifact_id"
        )

    redacted = redact_description(request.description)
    now = datetime.now(UTC)

    return SupportIncidentResponse(
        incident_id=f"INC-{uuid.uuid4().hex[:12].upper()}",
        status="received",
        category=request.category,
        redacted_description=redacted,
        created_at=now,
    )
