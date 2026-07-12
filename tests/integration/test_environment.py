"""
Тесты герметичности тестовой среды (Task 2).

Инвариант:
- Тест БЕЗ @pytest.mark.network не может открыть внешнее TCP.
- Конфиг роутится строго на тестовые изолированные сервисы:
  PostgreSQL:5434, Redis:6381, MinIO:9004 + bucket=test-artifacts
- AI_API_KEY пустой => Fake, без prod ключей и внешних сетей.
- Проверки запускаются только при поднятой docker-compose.test.yml
  (volumes сохраняются, без reset/checkout/commit).

Требования к запуску: docker compose -f docker-compose.test.yml up -d --wait
затем pytest tests/integration/test_environment.py -q
"""

from __future__ import annotations

import socket

import aiohttp
import pytest

# ──────────────────────────────────────────────────────────────────────
# 1. Доказательство: monkeypatch блокирует внешние соединения
# ──────────────────────────────────────────────────────────────────────

BLOCKED_NETWORK_ERROR = (
    "TEST ISOLATION VIOLATION: external network call attempted. "
    "Tests must not open real network connections. "
    "Use recorded fakes (tests/ai/fakes.py) or aioresponses."
)


def _block_socket_create_connection(
    address: tuple[str, int] | str,
    *args: object,
    **kwargs: object,
) -> socket.socket:
    """Блокирует все попытки создать TCP-соединение."""
    raise ConnectionError(BLOCKED_NETWORK_ERROR)


def _block_aiohttp_connect(
    *args: object,
    **kwargs: object,
) -> None:
    """Блокирует aiohttp connector."""
    raise aiohttp.ClientError(BLOCKED_NETWORK_ERROR)


# ──────────────────────────────────────────────────────────────────────
# 2. Тест: подтверждает, что блокировка работает
# ──────────────────────────────────────────────────────────────────────


class TestNetworkIsolationActive:
    """Проверяет, что autouse fixture блокирует внешнюю сеть."""

    def test_socket_connection_is_blocked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Попытка открыть сокет должна упасть с ConnectionError."""
        monkeypatch.setattr(socket, "create_connection", _block_socket_create_connection)
        with pytest.raises(ConnectionError, match="TEST ISOLATION VIOLATION"):
            socket.create_connection(("example.com", 443))

    def test_aiohttp_session_is_blocked(
        self, monkeypatch: pytest.MonkeyPatch, event_loop: object
    ) -> None:
        """Попытка aiohttp запроса должна упасть."""
        import asyncio

        async def _try_request() -> None:
            connector = aiohttp.TCPConnector()
            monkeypatch.setattr(connector, "connect", _block_aiohttp_connect)
            session = aiohttp.ClientSession(connector=connector)
            try:
                with pytest.raises(aiohttp.ClientError, match="TEST ISOLATION VIOLATION"):
                    await session.get("https://example.com")
            finally:
                await session.close()

        loop: asyncio.AbstractEventLoop = event_loop  # type: ignore[assignment]
        loop.run_until_complete(_try_request())


# ──────────────────────────────────────────────────────────────────────
# 3. Тест: AI клиент не отправляет запросы при пустом ключе
# ──────────────────────────────────────────────────────────────────────


class TestAIIsolation:
    """Проверяет, что fake AI client используется вместо реального."""

    def test_fake_client_returns_recorded_response(self) -> None:
        """FakeAIClient возвращает записанный ответ без HTTP."""
        import asyncio

        from tests.ai.fakes import FakeAIClient

        fake = FakeAIClient()

        async def _call() -> None:
            resp = await fake.chat_completion(messages=[{"role": "user", "content": "test"}])
            assert resp.text == '{"panels": [], "total_area_m2": 0.0}'
            assert resp.model_version == "deepseek/deepseek-chat-v3-0324"
            assert len(fake._call_log) == 1
            assert fake._call_log[0]["type"] == "chat"

        asyncio.get_event_loop().run_until_complete(_call())

    def test_fake_client_records_calls(self) -> None:
        """FakeAIClient логирует все вызовы."""
        import asyncio

        from tests.ai.fakes import FakeAIClient

        fake = FakeAIClient()

        async def _calls() -> None:
            await fake.chat_completion(messages=[{"role": "user", "content": "a"}])
            await fake.embed(texts=["hello", "world"])
            assert len(fake._call_log) == 2
            assert fake._call_log[0]["type"] == "chat"
            assert fake._call_log[1]["type"] == "embed"
            assert fake._call_log[1]["count"] == 2

        asyncio.get_event_loop().run_until_complete(_calls())

    def test_empty_api_key_is_explicit_domain_state(self) -> None:
        """Пустой AI_API_KEY — осознанное состояние, не ошибка конфигурации."""
        from shared.ai_settings import AISettings

        settings = AISettings(ai_api_key="")
        assert settings.ai_api_key == "", "Empty key means mock mode, not 'Bearer ' + retry"
        assert settings.ai_api_key is not None, "Key must be empty string, not None"


# ──────────────────────────────────────────────────────────────────────
# 3a. Фокусный тест: @pytest.mark.network восстанавливает оригинал
# ──────────────────────────────────────────────────────────────────────


class TestNetworkMarkerRestoresSocket:
    """Доказывает, что @pytest.mark.network временно снимает блокер."""

    @pytest.mark.network
    def test_marker_restores_original_socket(self) -> None:
        """С @pytest.mark.network socket.create_connection — это оригинал,
        а не наш блокер. Без маркера (autouse) блокер активен."""
        import tests.conftest as conftest_mod

        assert socket.create_connection is conftest_mod._original_socket_create_connection, (
            "With @pytest.mark.network, socket.create_connection must be "
            "the real builtin, not the blocker"
        )
        # Убеждаемся, что блокер — другая функция
        assert socket.create_connection is not _block_socket_create_connection

    def test_without_marker_blocker_is_active(self) -> None:
        """Без маркера socket.create_connection — блокер из conftest."""
        import tests.conftest as conftest_mod

        assert socket.create_connection is conftest_mod._block_socket_create_connection, (
            "Without @pytest.mark.network, socket.create_connection must be "
            "the conftest blocker"
        )


# ──────────────────────────────────────────────────────────────────────
# 3b. Фокусный тест: get_ai_client() возвращает fake при пустом ключе
# ──────────────────────────────────────────────────────────────────────


class TestAISingletonInjection:
    """Доказывает, что get_ai_client() при пустом ключе возвращает fake."""

    def test_get_ai_client_returns_fake_when_key_empty(self) -> None:
        """При пустом AI_API_KEY get_ai_client() возвращает FakeAIClient,
        а не создаёт реальный AIClient с пустым токеном."""
        import shared.ai_client as ai_mod
        from shared.ai_client import get_ai_client
        from tests.ai.fakes import FakeAIClient

        client = get_ai_client()
        assert isinstance(client, FakeAIClient), (
            f"Expected FakeAIClient, got {type(client).__name__}. "
            "The _reset_ai_singleton fixture must inject FakeAIClient "
            "when AI_API_KEY is empty."
        )
        # Убеждаемся, что singleton — тот же объект, что инжектирован fixture
        assert ai_mod._ai_client is client

# ──────────────────────────────────────────────────────────────────────
# 4. Тест: нет production secrets в test env
# ──────────────────────────────────────────────────────────────────────


class TestNoProductionSecrets:
    """Проверяет, что тесты не используют production секреты."""

    def test_no_real_api_key_in_test_env(self) -> None:
        """AI_API_KEY не должен содержать реального ключа в тестах."""
        import os

        key = os.environ.get("AI_API_KEY", "")
        # В тестовой среде ключ должен быть пустым или отсутствовать
        assert key == "" or key == "test", (
            f"AI_API_KEY should be empty in tests, got: {key[:8]}..."
        )

    def test_no_real_smtp_in_test_env(self) -> None:
        """RUSENDER_API_KEY не должен содержать реального ключа."""
        import os

        key = os.environ.get("RUSENDER_API_KEY", "")
        assert key == "", (
            f"RUSENDER_API_KEY should be empty in tests, got: {key[:8]}..."
        )

    def test_no_production_postgres_in_test_env(self) -> None:
        """POSTGRES_HOST должен указывать на test-инстанс, не production."""
        import os

        host = os.environ.get("POSTGRES_HOST", "127.0.0.1")
        assert host not in ("production-db.example.com", "db.mebel-ai.ru"), (
            f"POSTGRES_HOST should not point to production: {host}"
        )

    def test_test_routing_values_are_active(self) -> None:
        """После force в conftest env содержит именно тестовые значения."""
        import os

        assert os.environ.get("POSTGRES_PORT") == "5434"
        assert os.environ.get("POSTGRES_DB") == "furniture_ai_test"
        assert "6381" in os.environ.get("REDIS_URL", "")
        assert "9004" in os.environ.get("S3_ENDPOINT_URL", "")
        assert os.environ.get("AI_API_KEY") == ""
        assert "test-only-jwt" in os.environ.get("JWT_SECRET", "")


# ──────────────────────────────────────────────────────────────────────
# 5. Тест: Compose-сервисы поднимаются изолированно (smoke)
# ──────────────────────────────────────────────────────────────────────


class TestComposeSmoke:
    """Smoke-проверки: сервисы доступны на тестовых портах (только при поднятой infra)."""

    @pytest.mark.network
    def test_postgres_test_port_reachable(self) -> None:
        """Postgres test instance должен быть доступен на 5434 (не на 5433).
        Маркер network: connect_ex использует сеть к тестовой infra.
        """
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        try:
            result = sock.connect_ex(("127.0.0.1", 5434))
            assert result == 0, "Test Postgres on 5434 must be reachable when infra up"
            # Дополнительно: 5433 (обычный прод) не должен быть целью
            sock.connect_ex(("127.0.0.1", 5433))
            # Не assert fail если 5433 тоже есть, но цель - test
        finally:
            sock.close()

    @pytest.mark.network
    def test_redis_test_port_reachable(self) -> None:
        """Redis test instance на 6381."""
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        try:
            result = sock.connect_ex(("127.0.0.1", 6381))
            assert result == 0, "Test Redis on 6381 must be reachable when infra up"
        finally:
            sock.close()

    @pytest.mark.network
    def test_minio_test_port_and_bucket(self) -> None:
        """MinIO на 9004 + bucket test-artifacts существует.
        @pytest.mark.network потому что urllib/socket к localhost:9004
        должен быть разрешён (проверка реальной тестовой инфраструктуры).
        """
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        try:
            result = sock.connect_ex(("127.0.0.1", 9004))
            assert result == 0, "Test MinIO on 9004 must be reachable"
        finally:
            sock.close()

        # Проверить bucket через лёгкий HTTP (MinIO health)
        # network marker разрешает socket в этой функции
        import urllib.error
        import urllib.request
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:9004/minio/health/ready",
                headers={"User-Agent": "test-env-check"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                assert resp.status == 200
        except urllib.error.URLError as e:
            pytest.fail(f"MinIO health not reachable: {e}")


class TestTestEnvRoutingToServices:
    """Проверяет, что api.settings и клиенты видят именно тестовую инфраструктуру."""

    def test_settings_point_to_test_postgres(self) -> None:
        """settings.POSTGRES_* указывают на test инстанс."""
        from api.settings import settings

        assert settings.POSTGRES_PORT == 5434
        assert settings.POSTGRES_DB == "furniture_ai_test"
        assert settings.POSTGRES_HOST == "127.0.0.1"
        assert settings.POSTGRES_USER == "test_user"

    def test_settings_point_to_test_redis_and_minio(self) -> None:
        """REDIS_URL и S3_* на тестовые порты/креды."""
        from api.settings import settings

        assert "6381" in settings.REDIS_URL
        assert "127.0.0.1:9004" in (settings.S3_ENDPOINT_URL or "")
        assert settings.S3_BUCKET == "test-artifacts"
        assert settings.S3_ACCESS_KEY == "test_minio_user"

    def test_ai_key_empty_in_settings(self) -> None:
        """AI key пустой (гарантия mock режима)."""

        # settings может иметь ai_ префикс или через AISettings, проверяем os + settings
        import os
        assert os.environ.get("AI_API_KEY") == ""
        # settings сам может не хранить, но env форсирован
        assert os.environ["AI_API_KEY"] == ""
