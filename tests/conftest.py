"""Pytest fixtures для интеграционных тестов."""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.auth import create_access_token, get_current_user
from api.main import app
from api.models import Factory, User


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
