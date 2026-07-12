"""Ядро redaction для structured observability events.

Модуль чистый: только schema + redaction, без интеграций
(Sentry, провайдеры, main, worker).

Отложенные интеграции:
- Sentry: init.sentry_sdk(config) → интеграция через api/main.py
- Structured logging: structlog adapter → интеграция через api/worker.py
- Provider hooks: before/after AI calls → интеграция через api/ai/client.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# ── Регулярки для обнаружения чувствительных значений ─────────────────────

_BEARER_RE = re.compile(r"^Bearer\s+\S+", re.IGNORECASE)
_JWT_RE = re.compile(r"^[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+")
_HEX_TOKEN_RE = re.compile(r"^[0-9a-f]{32,}$", re.IGNORECASE)
_BASE64_TOKEN_RE = re.compile(r"^[A-Za-z0-9+/]{40,}={1,2}$")

# ── Множества имён полей для красного/жёлтого/зелёного списка ─────────────

# Всегда [REDACTED] — пароли, ключи, токены
_REDFIELD_NAMES: frozenset[str] = frozenset({
    "password", "passwd", "secret", "secret_key",
    "api_key", "apikey", "api-key",
    "access_key", "access_token",
    "s3_access_key", "s3_secret_key",
    "private_key", "jwt", "jwt_secret",
    "rusernder_api_key",
    "token", "bearer",
    "authorization",
    "cookie", "session",
})

# Содержимое AI-запроса/ответа (prompt, image data)
_PROMPTFIELD_NAMES: frozenset[str] = frozenset({
    "prompt", "system_prompt", "user_prompt",
    "content",  # может содержать промпт в AI-контексте
    "image", "image_data", "image_base64", "image_url",
})

# UUID/ID — маскируются до префикса (оставляем первые 8 символов)
_IDFIELD_NAMES: frozenset[str] = frozenset({
    "user_id", "factory_id", "order_id", "job_id",
})


class RedactLevel(int, Enum):
    """Уровень redaction. int для поддержки сравнений (<, >=)."""
    NONE = 0          # Без redaction
    LIGHT = 1         # Только auth/secret
    STANDARD = 2      # + prompt/image
    STRICT = 3        # + ID маскирование, все тексты


# ── Схема structured event ───────────────────────────────────────────────


@dataclass(frozen=True)
class ObservabilityEvent:
    """Structured event для observability pipeline.

    После redaction безопасен для Sentry/structlog/любого sink.
    """
    event_type: str           # "api.request", "ai.call", "auth.login" ...
    timestamp: datetime       # UTC
    severity: str             # "info", "warning", "error"
    data: dict[str, Any]      # payload (после redaction)
    context: dict[str, Any] = field(default_factory=dict)  # request_id, user_id ...

    def __post_init__(self) -> None:
        if not self.event_type:
            raise ValueError("event_type не может быть пустым")
        if self.severity not in ("debug", "info", "warning", "error", "critical"):
            raise ValueError(f"severity: допустимы debug/info/warning/error/critical, получено '{self.severity}'")


# ── Core redaction ───────────────────────────────────────────────────────


def redact_value(value: Any, field_name: str = "", level: RedactLevel = RedactLevel.STANDARD) -> Any:
    """Redact одну строку/значение.

    Rules:
    1. field_name в REDFIELD_NAMES → всегда [REDACTED]
    2. Значение совпадает с bearer/jwt/hex/base64 паттерном → [REDACTED]
    3. field_name в PROMPTFIELD_NAMES → [REDACTED] (при level >= STANDARD)
    4. field_name в IDFIELD_NAMES → маскирование (при level >= STRICT)
    5. Текст >500 символов → обрезка + [TRUNCATED]
    6. None/bool/int/float → как есть
    """
    name_lower = field_name.lower().strip()
    # 1. Красный список — всегда красим (включая bool/int значения)
    if name_lower in _REDFIELD_NAMES:
        return "[REDACTED]"

    # 2. Значение похоже на токен/secret
    if isinstance(value, str) and _looks_like_secret(value):
        return "[REDACTED]"

    if level >= RedactLevel.STANDARD and name_lower in _PROMPTFIELD_NAMES:
        return "[REDACTED]"

    # 4. ID поля — маскирование при STRICT (до None/bool/int passthrough)
    if level >= RedactLevel.STRICT and name_lower in _IDFIELD_NAMES:
        if isinstance(value, str) and len(value) > 8:
            return value[:8] + "[...MASKED]"
        return "[...MASKED]"

    if value is None or isinstance(value, (int, float, bool)):
        return value

    # 5. Длинные строки
    if isinstance(value, str) and len(value) > 500:
        return value[:500] + "...[TRUNCATED]"

    return value


def redact_dict(
    data: dict[str, Any],
    level: RedactLevel = RedactLevel.STANDARD,
    *,
    additional_redact_fields: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Рекурсивно redact все значения в dict.

    Args:
        data: исходный dict
        level: уровень redaction
        additional_redact_fields: доп. имена полей для красного списка
    """
    red_fields = _REDFIELD_NAMES
    if additional_redact_fields:
        red_fields = red_fields | additional_redact_fields

    result: dict[str, Any] = {}
    for key, value in data.items():
        name_lower = key.lower().strip()

        # Красный список
        if name_lower in red_fields:
            result[key] = "[REDACTED]"
            continue

        # Значение похоже на секрет
        if isinstance(value, str) and _looks_like_secret(value):
            result[key] = "[REDACTED]"
            continue

        # Prompt/image поля
        if level >= RedactLevel.STANDARD and name_lower in _PROMPTFIELD_NAMES:
            result[key] = "[REDACTED]"
            continue

        # ID поля — маскирование при STRICT
        if level >= RedactLevel.STRICT and name_lower in _IDFIELD_NAMES:
            if isinstance(value, str) and len(value) > 8:
                result[key] = value[:8] + "[...MASKED]"
            else:
                result[key] = "[...MASKED]"
            continue

        # Рекурсия для вложенных структур
        if isinstance(value, dict):
            result[key] = redact_dict(value, level, additional_redact_fields=additional_redact_fields)
        elif isinstance(value, list):
            result[key] = redact_list(value, level, additional_redact_fields=additional_redact_fields)
        elif isinstance(value, str) and len(value) > 500:
            result[key] = value[:500] + "...[TRUNCATED]"
        else:
            result[key] = value

    return result


def redact_list(
    items: list[Any],
    level: RedactLevel = RedactLevel.STANDARD,
    *,
    additional_redact_fields: frozenset[str] | None = None,
) -> list[Any]:
    """Рекурсивно redact элементы списка."""
    result: list[Any] = []
    for item in items:
        if isinstance(item, dict):
            result.append(redact_dict(item, level, additional_redact_fields=additional_redact_fields))
        elif isinstance(item, list):
            result.append(redact_list(item, level, additional_redact_fields=additional_redact_fields))
        elif isinstance(item, str) and len(item) > 500:
            result.append(item[:500] + "...[TRUNCATED]")
        else:
            result.append(item)
    return result


def _looks_like_secret(value: str) -> bool:
    """Эвристика: похоже ли строковое значение на секрет/токен."""
    if not isinstance(value, str) or not value:
        return False
    value = value.strip()

    # Bearer токен
    if _BEARER_RE.match(value):
        return True
    # JWT (xxx.yyy.zzz)
    if _JWT_RE.match(value):
        return True
    # Длинный hex (API keys)
    if len(value) >= 32 and _HEX_TOKEN_RE.match(value):
        return True
    # Base64-encoded (image data, tokens)
    if len(value) >= 40 and _BASE64_TOKEN_RE_MATCH(value):
        return True

    return False


def _BASE64_TOKEN_RE_MATCH(value: str) -> bool:
    """Проверка base64 — не путать с именем regex."""
    return bool(_BASE64_TOKEN_RE.match(value))


# ── Public API: создание event ───────────────────────────────────────────


def create_event(
    event_type: str,
    data: dict[str, Any],
    *,
    severity: str = "info",
    context: dict[str, Any] | None = None,
    level: RedactLevel = RedactLevel.STANDARD,
    additional_redact_fields: frozenset[str] | None = None,
) -> ObservabilityEvent:
    """Создать structured event с автоматическим redaction."""
    redacted_data = redact_dict(data, level, additional_redact_fields=additional_redact_fields)
    redacted_context = redact_dict(context or {}, level, additional_redact_fields=additional_redact_fields)
    return ObservabilityEvent(
        event_type=event_type,
        timestamp=datetime.now(UTC),
        severity=severity,
        data=redacted_data,
        context=redacted_context,
    )


def event_to_dict(event: ObservabilityEvent) -> dict[str, Any]:
    """Сериализовать event в dict для логов/JSON sinks."""
    return {
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "severity": event.severity,
        "data": event.data,
        "context": event.context,
    }
