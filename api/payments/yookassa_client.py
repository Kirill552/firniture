"""Клиент ЮKassa API v3 (https://yookassa.ru/developers/api).

Аутентификация — HTTP Basic (shop_id : secret_key), ключ идемпотентности
передаётся заголовком `Idempotence-Key` (обязателен для POST /payments).

MOCK-режим: без ключей магазина сеть отключается, но только когда явно задан
`MOCK_MODE=true`. На проде без ключей checkout падает с YooKassaError, чтобы
клиент не уехал по мёртвой ссылке вместо страницы оплаты.

Чеки (54-ФЗ) не формируем: самозанятый проводит их вне нашего кода,
поле `receipt` в запросах не передаём.
"""

from __future__ import annotations

import logging
import os
import uuid
from decimal import Decimal
from typing import Any

import aiohttp

from api.settings import settings

log = logging.getLogger(__name__)

API_BASE_URL = "https://api.yookassa.ru/v3"
REQUEST_TIMEOUT_SECONDS = 20
MOCK_CONFIRMATION_URL = "https://yookassa.mock.local/checkout"


class YooKassaError(RuntimeError):
    """Ошибка обращения к ЮKassa — сеть или не-2xx ответ."""


def new_idempotence_key() -> str:
    """Ключ идемпотентности: UUID4 без дефисов укладывается в 64 символа."""
    return uuid.uuid4().hex


def _assert_mock_allowed() -> None:
    """MOCK-платежи разрешены только при явном MOCK_MODE (dev и тесты)."""
    if os.getenv("MOCK_MODE", "false").lower() not in ("true", "1", "yes"):
        raise YooKassaError(
            "Платежи не настроены: задайте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY"
        )


def format_amount(amount_rub: int | Decimal) -> str:
    """Сумма в формате ЮKassa: строка с двумя знаками после точки."""
    return f"{Decimal(amount_rub):.2f}"


class YooKassaClient:
    """Асинхронный клиент платежей ЮKassa на aiohttp."""

    def __init__(self) -> None:
        self.shop_id = settings.YOOKASSA_SHOP_ID
        self.secret_key = settings.YOOKASSA_SECRET_KEY
        self.is_mock = not self.shop_id or not self.secret_key
        self._session: aiohttp.ClientSession | None = None

        if self.is_mock:
            log.warning("YOOKASSA_SHOP_ID/SECRET_KEY не заданы — работаем в MOCK-режиме")

    async def close(self) -> None:
        """Закрыть HTTP-сессию (вызывается на shutdown приложения)."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ленивое создание aiohttp-сессии с Basic-auth магазина."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                auth=aiohttp.BasicAuth(self.shop_id, self.secret_key),
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
            )
        return self._session

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        idempotence_key: str | None = None,
    ) -> dict[str, Any]:
        """Один запрос к API. Любой не-2xx превращается в YooKassaError."""
        session = await self._ensure_session()
        headers = {"Content-Type": "application/json"}
        if idempotence_key:
            headers["Idempotence-Key"] = idempotence_key

        try:
            async with session.request(
                method, f"{API_BASE_URL}{path}", json=json_data, headers=headers
            ) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    log.warning("ЮKassa %s %s → %s: %s", method, path, resp.status, body[:300])
                    raise YooKassaError(f"HTTP {resp.status}: {body[:300]}")
                return await resp.json()
        except (TimeoutError, aiohttp.ClientError) as exc:
            raise YooKassaError(f"Сеть недоступна: {exc}") from exc

    async def create_payment(
        self,
        amount_rub: int | Decimal,
        description: str,
        return_url: str,
        metadata: dict[str, str],
        idempotence_key: str,
    ) -> dict[str, Any]:
        """POST /payments — создать платёж с редиректом на страницу оплаты."""
        if self.is_mock:
            _assert_mock_allowed()
            return _mock_payment(amount_rub, idempotence_key, metadata)

        payload = {
            "amount": {"value": format_amount(amount_rub), "currency": "RUB"},
            "description": description[:128],
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": return_url},
            "metadata": metadata,
        }
        return await self._request(
            "POST", "/payments", json_data=payload, idempotence_key=idempotence_key
        )

    async def get_payment(self, payment_id: str) -> dict[str, Any]:
        """GET /payments/{id} — актуальное состояние платежа (SSOT для вебхука)."""
        if self.is_mock:
            _assert_mock_allowed()
            return _mock_payment_status(payment_id)
        return await self._request("GET", f"/payments/{payment_id}")


def _mock_payment(
    amount_rub: int | Decimal, idempotence_key: str, metadata: dict[str, str]
) -> dict[str, Any]:
    """Ответ MOCK-режима на создание платежа — сеть не трогаем."""
    payment_id = f"mock-{idempotence_key[:28]}"
    log.warning(
        "MOCK ЮKassa: платёж %s на %s ₽, metadata=%s",
        payment_id,
        format_amount(amount_rub),
        metadata,
    )
    return {
        "id": payment_id,
        "status": "pending",
        "paid": False,
        "amount": {"value": format_amount(amount_rub), "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "confirmation_url": f"{MOCK_CONFIRMATION_URL}/{payment_id}",
        },
        "metadata": metadata,
    }


def _mock_payment_status(payment_id: str) -> dict[str, Any]:
    """Ответ MOCK-режима на запрос статуса: платёж успешен."""
    log.warning("MOCK ЮKassa: статус платежа %s = succeeded", payment_id)
    return {"id": payment_id, "status": "succeeded", "paid": True}


_client: YooKassaClient | None = None


def get_yookassa_client() -> YooKassaClient:
    """Singleton клиента — переиспользуем HTTP-сессию между запросами."""
    global _client
    if _client is None:
        _client = YooKassaClient()
    return _client
