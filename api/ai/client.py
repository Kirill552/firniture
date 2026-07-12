"""Инъецируемый транспорт AI-провайдера с ограниченными безопасными повторами."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol

import aiohttp

from api.ai.contracts import (
    ProviderRequest,
    ProviderResponse,
    ProviderSettings,
    ProviderTransportError,
    TransportErrorKind,
    compute_retry_delay_seconds,
    is_retryable_status,
)


class ProviderSender(Protocol):
    """Адаптер HTTP SDK; реализация остаётся за boundary-интеграцией."""

    def __call__(self, request: ProviderRequest) -> Awaitable[ProviderResponse]: ...


Sleep = Callable[[float], Awaitable[None]]


class ProviderAwareAIClient:
    """Выполняет запросы через переданный sender и не создаёт сетевых сессий сам."""

    def __init__(
        self,
        settings: ProviderSettings,
        sender: ProviderSender,
        *,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._sender = sender
        self._sleep = sleep

    async def execute(self, *, operation: str, payload: Mapping[str, Any]) -> ProviderResponse:
        """Вернуть успешный ответ или типизированную, безопасную ошибку транспорта."""
        request = ProviderRequest(
            provider=self._settings.provider,
            operation=operation,
            payload=payload,
        )
        for attempts in range(1, self._settings.max_attempts + 1):
            failure, response = await self._attempt(request, attempts)
            if response is not None:
                return response
            if failure is None:
                raise RuntimeError("Транспорт не вернул ни ответ, ни ошибку")
            if not failure.retryable or attempts == self._settings.max_attempts:
                raise failure from None
            await self._sleep(compute_retry_delay_seconds(attempts))
        raise RuntimeError("Цикл повторных попыток завершился неожиданно")

    async def _attempt(
        self, request: ProviderRequest, attempts: int
    ) -> tuple[ProviderTransportError | None, ProviderResponse | None]:
        try:
            response = await self._sender(request)
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            return self._failure(
                request, TransportErrorKind.TIMEOUT, attempts=attempts, retryable=True
            ), None
        except (ConnectionError, aiohttp.ClientConnectionError):
            return self._failure(
                request, TransportErrorKind.DISCONNECT, attempts=attempts, retryable=True
            ), None
        except Exception:
            return self._failure(
                request, TransportErrorKind.UNEXPECTED, attempts=attempts, retryable=False
            ), None

        if not isinstance(response, ProviderResponse) or response.provider != request.provider:
            return self._failure(
                request, TransportErrorKind.MALFORMED_RESPONSE, attempts=attempts, retryable=False
            ), None
        if 200 <= response.status_code <= 299:
            return None, response
        return self._failure(
            request,
            TransportErrorKind.HTTP_STATUS,
            attempts=attempts,
            retryable=is_retryable_status(response.status_code),
            status_code=response.status_code,
        ), None

    @staticmethod
    def _failure(
        request: ProviderRequest,
        kind: TransportErrorKind,
        *,
        attempts: int,
        retryable: bool,
        status_code: int | None = None,
    ) -> ProviderTransportError:
        return ProviderTransportError(
            provider=request.provider,
            operation=request.operation,
            kind=kind,
            attempts=attempts,
            retryable=retryable,
            status_code=status_code,
        )
