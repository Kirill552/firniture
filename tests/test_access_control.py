"""Тесты контроля доступа к ресурсам фабрики."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.access_control import enforce_factory_access, has_factory_access


class TestHasFactoryAccess:
    """Проверка матрицы доступа."""

    def test_allows_anonymous_resource_without_user(self) -> None:
        """Анонимный ресурс доступен без авторизации."""
        assert has_factory_access(resource_factory_id=None, user_factory_id=None) is True

    def test_denies_tenant_resource_without_user(self) -> None:
        """Приватный ресурс фабрики требует авторизацию."""
        assert has_factory_access(resource_factory_id=uuid4(), user_factory_id=None) is False

    def test_allows_same_factory(self) -> None:
        """Ресурс доступен пользователю своей фабрики."""
        factory_id = uuid4()
        assert has_factory_access(resource_factory_id=factory_id, user_factory_id=factory_id) is True

    def test_denies_foreign_factory(self) -> None:
        """Ресурс чужой фабрики недоступен."""
        assert has_factory_access(resource_factory_id=uuid4(), user_factory_id=uuid4()) is False


class TestEnforceFactoryAccess:
    """Проверка HTTP-ошибок для API."""

    def test_raises_unauthorized_for_private_resource(self) -> None:
        """Без пользователя доступ к приватному ресурсу запрещён."""
        with pytest.raises(HTTPException) as exc_info:
            enforce_factory_access(resource_factory_id=uuid4(), user_factory_id=None)
        assert exc_info.value.status_code == 401

    def test_raises_forbidden_for_foreign_factory(self) -> None:
        """Чужой resource factory_id возвращает 403."""
        with pytest.raises(HTTPException) as exc_info:
            enforce_factory_access(resource_factory_id=uuid4(), user_factory_id=uuid4())
        assert exc_info.value.status_code == 403
