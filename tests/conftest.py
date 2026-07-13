"""
Pytest fixtures для тестов.

Герметичность тестовой среды (Task 2):
- Session-scoped autouse: блокирует внешние TCP (кроме @pytest.mark.network).
- Роутинг на изолированные test PostgreSQL (5434), Redis (6381), MinIO (9004).
- AI_API_KEY="" => всегда FakeAIClient, без реальных вызовов к AI.
- Нет production secrets (JWT тестовый, ключи пустые или test_*).
- os.environ override происходит ДО импорта api.* (settings/database/main).
- aiohttp cleanup + AI singleton reset.

Инфраструктура поднимается отдельно: docker compose -f docker-compose.test.yml up -d --wait
volumes не удаляются, внешняя сеть/прод не используется.
"""

from __future__ import annotations

import asyncio
import os
import socket
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from uuid import UUID

import aiohttp
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ── EARLY: hermetic test env routing (BEFORE any api.* or shared settings import) ──
# This ensures Settings() in api/settings.py and derived DB/Redis/S3 clients
# see test ports/creds, not values from .env or defaults.
# pydantic-settings prioritizes os.environ over env_file.


def _force_test_environment_routing() -> None:
    """Загружает тестовые значения из .env.test.example и принудительно переопределяет
    ключи для гарантированной маршрутизации на тестовые сервисы.
    Вызывается на import conftest (до тестов и до импортов api).
    """
    root = Path(__file__).resolve().parents[1]
    env_example = root / ".env.test.example"

    # 1. Загрузить из .env.test.example если есть (простой парсер, без доп. deps)
    if env_example.is_file():
        for raw in env_example.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key:
                os.environ[key] = value

    # 2. Жёстко форсируем тестовые порты/креды/моки (приоритет, даже если .env.test.example изменён)
    # Postgres test instance
    os.environ["POSTGRES_HOST"] = "127.0.0.1"
    os.environ["POSTGRES_PORT"] = "5434"
    os.environ["POSTGRES_DB"] = "furniture_ai_test"
    os.environ["POSTGRES_USER"] = "test_user"
    os.environ["POSTGRES_PASSWORD"] = "test_only_password"

    # Redis test
    os.environ["REDIS_URL"] = "redis://:test_redis_password@127.0.0.1:6381/0"

    # MinIO / S3 test (isolated)
    os.environ["S3_ENDPOINT_URL"] = "http://127.0.0.1:9004"
    os.environ["S3_ACCESS_KEY"] = "test_minio_user"
    os.environ["S3_SECRET_KEY"] = "test_minio_secret_2026"
    os.environ["S3_BUCKET"] = "test-artifacts"

    # AI: empty key => mock mode (no external calls, no prod keys)
    os.environ["AI_API_KEY"] = ""
    os.environ["AI_BASE_URL"] = ""

    # JWT test only (never prod)
    os.environ["JWT_SECRET"] = "test-only-jwt-secret-not-for-production"

    # Тестовые значения защиты гостевой загрузки для герметичных тестов (Task 1).
    os.environ["GUEST_UPLOAD_SECRET"] = "test-guest-upload-secret-32bytes-minimum-2026"
    os.environ["TRUSTED_PROXY_CIDRS"] = "127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    # Email / external: mock
    os.environ["RUSENDER_API_KEY"] = ""

    # Ensure we never accidentally pick prod hosts from any leftover
    # (defensive; real prod would be different names anyway)
    forbidden_prod_hosts = {"db.mebel-ai.ru", "production-db.example.com", "localhost:5433"}
    if os.environ.get("POSTGRES_HOST", "") in forbidden_prod_hosts:
        os.environ["POSTGRES_HOST"] = "127.0.0.1"


_force_test_environment_routing()


# api imports AFTER env is forced
from api.auth import create_access_token, get_current_user
from api.database import SessionLocal
from api.main import app
from api.models import Factory, User

# ── Network blocking (hermetic test environment) ─────────────────────

_NETWORK_BLOCKED = False

_BLOCK_MSG = (
    "TEST ISOLATION VIOLATION: external network call attempted. "
    "Tests must not open real network connections. "
    "Use recorded fakes (tests/ai/fakes.py) or aioresponses."
)


def _block_socket_create_connection(
    address: tuple[str, int] | str,
    *args: object,
    **kwargs: object,
) -> socket.socket:
    raise ConnectionError(_BLOCK_MSG)

# Snapshot the *real* builtin before any fixture touches it.
# Session and per-test fixtures reference this constant — never re-read
# socket.create_connection at runtime (it would already be the blocker).
_original_socket_create_connection = socket.create_connection

@pytest.fixture(autouse=True, scope="session")
def _block_network_session() -> None:
    """
    Session-scoped autouse: блокирует все TCP-соединения через socket.
    Тесты с @pytest.mark.network получают отдельный monkeypatch-откат.
    """
    global _NETWORK_BLOCKED
    socket.create_connection = _block_socket_create_connection  # type: ignore[assignment]
    _NETWORK_BLOCKED = True
    yield
    socket.create_connection = _original_socket_create_connection  # type: ignore[assignment]
    _NETWORK_BLOCKED = False


@pytest.fixture(autouse=True, scope="function")
def _block_network_per_test(request: pytest.FixtureRequest) -> None:
    """
    Per-test: для @pytest.mark.network временно разблокирует socket,
    используя заранее сохранённый оригинал (не текущее значение,
    которое к этому моменту уже блокер).
    """
    if request.node.get_closest_marker("network"):
        socket.create_connection = _original_socket_create_connection  # type: ignore[assignment]
        yield
        socket.create_connection = _block_socket_create_connection  # type: ignore[assignment]
    else:
        yield


# ── AI singleton reset ──────────────────────────────────────────────

@pytest.fixture(autouse=True, scope="function")
def _reset_ai_singleton() -> None:
    """Сбрасывает singleton AIClient между тестами.

    При пустом AI_API_KEY (тестовый режим) подставляет FakeAIClient,
    чтобы get_ai_client() никогда не создавал реальный AIClient
    с пустым ключом и не пытался ретраить live-запросы.
    """
    import shared.ai_client as ai_mod
    from tests.ai.fakes import FakeAIClient

    old_client = ai_mod._ai_client

    # Пустой ключ = mock-режим: подставляем фейк, а не None,
    # иначе get_ai_client() построит реальный AIClient(settings).
    if os.environ.get("AI_API_KEY", "") == "":
        ai_mod._ai_client = FakeAIClient()
    else:
        ai_mod._ai_client = None

    yield

    # Закрываем тестовую сессию и восстанавливаем
    if ai_mod._ai_client is not None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(ai_mod._ai_client.close())
            else:
                loop.run_until_complete(ai_mod._ai_client.close())
        except RuntimeError:
            pass
    ai_mod._ai_client = old_client


# ── aiohttp session cleanup ─────────────────────────────────────────

_active_sessions: list[aiohttp.ClientSession] = []


@pytest.fixture(autouse=True, scope="function")
def _cleanup_aiohttp_sessions() -> None:
    """Закрывает все aiohttp-сессии после каждого теста."""
    yield
    for session in _active_sessions[:]:
        if not session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(session.close())
                else:
                    loop.run_until_complete(session.close())
            except RuntimeError:
                pass
    _active_sessions.clear()


# ── Test environment markers ────────────────────────────────────────

def pytest_configure(config: pytest.Config) -> None:
    """Регистрирует кастомные маркеры."""
    config.addinivalue_line("markers", "network: разрешает реальные сетевые вызовы")


# Тестовые UUID
TEST_FACTORY_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_ID = UUID("87654321-4321-8765-4321-876543218765")


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP клиент для тестирования API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_factory() -> Factory:
    """Мок фабрики для тестов."""
    factory = Factory(
        id=TEST_FACTORY_ID,
        name="Test Factory"
    )
    return factory


@pytest.fixture
def mock_user(mock_factory: Factory) -> User:
    """Мок пользователя для тестов."""
    user = User(
        id=TEST_USER_ID,
        email="test@example.com",
        factory_id=mock_factory.id,
        is_owner=True
    )
    # Прикрепляем фабрику к пользователю (для SQLAlchemy relationship)
    user.factory = mock_factory
    return user


@pytest.fixture
def auth_headers(mock_user: User) -> dict[str, str]:
    """Заголовки авторизации с JWT токеном."""
    token, _ = create_access_token(mock_user.id, mock_user.factory_id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, mock_user: User) -> AsyncGenerator[AsyncClient, None]:
    """HTTP клиент с переопределённой аутентификацией."""
    # Auth is overridden with an in-memory user, but orders enforce the real FK.
    async with SessionLocal() as session:
        await session.merge(Factory(id=mock_user.factory_id, name="Test Factory"))
        await session.merge(
            User(
                id=mock_user.id,
                email=mock_user.email,
                factory_id=mock_user.factory_id,
                is_owner=mock_user.is_owner,
            )
        )
        await session.commit()

    async def mock_get_current_user():
        return mock_user

    # Переопределяем dependency
    app.dependency_overrides[get_current_user] = mock_get_current_user

    yield client

    # Очищаем переопределения после теста
    app.dependency_overrides.clear()


@pytest.fixture
def wall_cabinet_request() -> dict[str, Any]:
    """Запрос для навесного шкафа."""
    return {
        "cabinet_type": "wall",
        "width_mm": 600,
        "height_mm": 720,
        "depth_mm": 300,
        "shelf_count": 2,
    }


@pytest.fixture
def base_cabinet_request() -> dict[str, Any]:
    """Запрос для напольной тумбы."""
    return {
        "cabinet_type": "base",
        "width_mm": 600,
        "height_mm": 720,
        "depth_mm": 560,
        "shelf_count": 1,
    }


@pytest.fixture
def drawer_cabinet_request() -> dict[str, Any]:
    """Запрос для тумбы с ящиками."""
    return {
        "cabinet_type": "drawer",
        "width_mm": 600,
        "height_mm": 720,
        "depth_mm": 560,
        "drawer_count": 3,
    }


@pytest.fixture
def bom_request() -> dict[str, Any]:
    """Запрос для генерации BOM."""
    return {
        "cabinet_type": "base",
        "width_mm": 600,
        "height_mm": 720,
        "depth_mm": 560,
        "door_count": 2,
        "shelf_count": 1,
    }


@pytest_asyncio.fixture
async def async_client(authenticated_client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    """Alias для authenticated_client для совместимости с тестами."""
    yield authenticated_client


@pytest_asyncio.fixture
async def created_order(async_client: AsyncClient) -> AsyncGenerator[dict[str, Any], None]:
    """Создаёт тестовый заказ и возвращает его данные."""
    order_data = {
        "name": "Тестовый заказ",
        "description": "Заказ для тестирования",
    }
    response = await async_client.post("/api/v1/orders", json=order_data)
    assert response.status_code == 200, f"Failed to create order: {response.text}"
    yield response.json()
