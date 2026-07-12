"""Контракты изолированного транспорта AI-провайдеров без сетевой интеграции."""

from __future__ import annotations

import random
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any
from urllib.parse import urlparse

from shared.ai_settings import AISettings


class TransportMode(StrEnum):
    """Явно разделяет локальную имитацию и production-транспорт."""

    LOCAL_MOCK = "local_mock"
    PRODUCTION = "production"


class TransportErrorKind(StrEnum):
    """Стабильные причины ошибки, безопасные для журналирования."""

    HTTP_STATUS = "http_status"
    TIMEOUT = "timeout"
    DISCONNECT = "disconnect"
    MALFORMED_RESPONSE = "malformed_response"
    UNEXPECTED = "unexpected"


@dataclass(frozen=True)
class ProviderSettings:
    """Явный контракт конфигурации без чтения settings или секретов из окружения."""

    provider: str
    mode: TransportMode
    base_url: str | None = None
    api_key: str | None = None
    max_attempts: int = 3

    def __post_init__(self) -> None:
        _require_text(self.provider, "provider")
        if not 1 <= self.max_attempts <= 5:
            raise ValueError("max_attempts должен быть от 1 до 5")
        if self.mode is TransportMode.LOCAL_MOCK:
            if self.base_url is not None or self.api_key is not None:
                raise ValueError("local mock не принимает URL или ключ провайдера")
            if self.max_attempts != 1:
                raise ValueError("local mock должен выполняться без повторных попыток")
            return
        if self.mode is not TransportMode.PRODUCTION:
            raise ValueError("mode должен быть local_mock или production")
        if not _is_https_url(self.base_url) or not _is_nonempty_text(self.api_key):
            raise ValueError("production требует HTTPS URL и непустой ключ провайдера")

    @classmethod
    def local_mock(cls, provider: str = "local-mock") -> ProviderSettings:
        """Создать настройки для локального обработчика без credentials."""
        return cls(provider=provider, mode=TransportMode.LOCAL_MOCK, max_attempts=1)


@dataclass(frozen=True)
class ProviderRequest:
    """Запрос к внедряемому sender; payload не попадает в диагностические ошибки."""

    provider: str
    operation: str
    payload: Mapping[str, Any] = field(repr=False)

    def __post_init__(self) -> None:
        _require_text(self.provider, "provider")
        _require_text(self.operation, "operation")
        if not isinstance(self.payload, Mapping):
            raise ValueError("payload должен быть объектом")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


@dataclass(frozen=True)
class ProviderResponse:
    """Ответ sender до разбора provider-специфичного тела."""

    provider: str
    status_code: int
    payload: Mapping[str, Any] = field(repr=False)
    request_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.provider, "provider")
        if isinstance(self.status_code, bool) or not isinstance(self.status_code, int):
            raise ValueError("status_code должен быть целым числом")
        if not 100 <= self.status_code <= 599:
            raise ValueError("status_code должен быть HTTP-кодом")
        if not isinstance(self.payload, Mapping):
            raise ValueError("payload должен быть объектом")
        if self.request_id is not None:
            _require_text(self.request_id, "request_id")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


class ProviderTransportError(RuntimeError):
    """Ошибка транспорта без URL, ключа, prompt или сырого тела provider-ответа."""

    def __init__(
        self,
        *,
        provider: str,
        operation: str,
        kind: TransportErrorKind,
        attempts: int,
        retryable: bool,
        status_code: int | None = None,
    ) -> None:
        self.provider = provider
        self.operation = operation
        self.kind = kind
        self.attempts = attempts
        self.retryable = retryable
        self.status_code = status_code
        detail = f"provider={provider} operation={operation} kind={kind} attempts={attempts}"
        if status_code is not None:
            detail = f"{detail} status={status_code}"
        super().__init__(detail)


def is_retryable_status(status_code: int) -> bool:
    """Повторять только явные временные HTTP-сбои."""
    return status_code in (408, 429) or 500 <= status_code <= 599


RETRY_BASE_DELAYS_SECONDS = (0.25, 0.5, 1.0, 2.0)
_JITTER_RATIO = 0.5


def compute_retry_delay_seconds(attempt: int) -> float:
    """Вернуть ограниченную задержку повтора со случайным разбросом ±50% вокруг шага.

    Джиттер снижает риск thundering herd при одновременных повторах у многих клиентов.
    """
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        raise ValueError("attempt должен быть положительным целым числом")
    base = RETRY_BASE_DELAYS_SECONDS[min(attempt - 1, len(RETRY_BASE_DELAYS_SECONDS) - 1)]
    jitter_span = base * _JITTER_RATIO
    return base + random.uniform(-jitter_span, jitter_span)


def provider_settings_from_ai_settings(
    settings: AISettings, *, provider: str = "openrouter"
) -> ProviderSettings:
    """Fail-closed мост от легаси AISettings к provider-aware транспорту.

    Пустой ``ai_api_key`` — единственный явный триггер local mock; production
    требует HTTPS base_url и непустой ключ (см. ``ProviderSettings.__post_init__``),
    поэтому неполная или повреждённая production-конфигурация падает здесь же,
    а не посреди первого реального запроса.
    """
    if not settings.ai_api_key:
        return ProviderSettings.local_mock(provider=provider)
    return ProviderSettings(
        provider=provider,
        mode=TransportMode.PRODUCTION,
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key,
    )


def _is_https_url(value: str | None) -> bool:
    if not _is_nonempty_text(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _require_text(value: object, field_name: str) -> None:
    if not _is_nonempty_text(value):
        raise ValueError(f"{field_name} должен быть непустой строкой")


def _is_nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
