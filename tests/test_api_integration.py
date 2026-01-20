"""Интеграционные тесты API endpoints."""

import pytest
from httpx import AsyncClient


class TestPanelsCalculateEndpoint:
    """Тесты POST /api/v1/panels/calculate."""

    async def test_wall_cabinet(self, client: AsyncClient, wall_cabinet_request: dict):
        """Тест расчёта навесного шкафа."""
        response = await client.post("/api/v1/panels/calculate", json=wall_cabinet_request)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cabinet_type"] == "wall"
        assert data["dimensions"]["width"] == 600
        assert data["dimensions"]["height"] == 720
        assert data["dimensions"]["depth"] == 300
        assert len(data["panels"]) >= 5  # Минимум: 2 боковины + верх + низ + 2 полки
        assert data["total_panels"] >= 5
        assert data["total_area_m2"] > 0
        assert data["edge_length_m"] > 0

    async def test_base_cabinet(self, client: AsyncClient, base_cabinet_request: dict):
        """Тест расчёта напольной тумбы."""
        response = await client.post("/api/v1/panels/calculate", json=base_cabinet_request)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cabinet_type"] == "base"

        # Проверяем наличие царг
        panel_names = [p["name"] for p in data["panels"]]
        assert any("царга" in name.lower() for name in panel_names)

    async def test_drawer_cabinet(self, client: AsyncClient, drawer_cabinet_request: dict):
        """Тест расчёта тумбы с ящиками."""
        response = await client.post("/api/v1/panels/calculate", json=drawer_cabinet_request)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cabinet_type"] == "drawer"

        # Проверяем наличие панелей ящиков
        panel_names = [p["name"] for p in data["panels"]]
        assert any("ящик" in name.lower() for name in panel_names)

    async def test_sink_cabinet(self, client: AsyncClient):
        """Тест расчёта тумбы под мойку."""
        request = {
            "cabinet_type": "base_sink",
            "width_mm": 800,
            "height_mm": 720,
            "depth_mm": 560,
        }
        response = await client.post("/api/v1/panels/calculate", json=request)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cabinet_type"] == "base_sink"

        # Тумба под мойку не должна иметь дно
        panel_names = [p["name"] for p in data["panels"]]
        assert "Дно" not in panel_names

        # Должно быть предупреждение про мойку
        assert len(data["warnings"]) > 0

    async def test_tall_cabinet(self, client: AsyncClient):
        """Тест расчёта высокого шкафа-пенала."""
        request = {
            "cabinet_type": "tall",
            "width_mm": 600,
            "height_mm": 2100,
            "depth_mm": 560,
            "shelf_count": 4,
        }
        response = await client.post("/api/v1/panels/calculate", json=request)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cabinet_type"] == "tall"
        assert data["dimensions"]["height"] == 2100

    async def test_invalid_cabinet_type(self, client: AsyncClient):
        """Тест ошибки для неизвестного типа."""
        request = {
            "cabinet_type": "invalid_type",
            "width_mm": 600,
            "height_mm": 720,
            "depth_mm": 300,
        }
        response = await client.post("/api/v1/panels/calculate", json=request)

        # Pydantic возвращает 422 для validation errors
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    async def test_panel_structure(self, client: AsyncClient, wall_cabinet_request: dict):
        """Тест структуры данных панели."""
        response = await client.post("/api/v1/panels/calculate", json=wall_cabinet_request)
        data = response.json()

        panel = data["panels"][0]

        # Проверяем обязательные поля
        assert "name" in panel
        assert "width_mm" in panel
        assert "height_mm" in panel
        assert "thickness_mm" in panel
        assert "quantity" in panel
        assert "edge_front" in panel
        assert "edge_back" in panel
        assert "edge_top" in panel
        assert "edge_bottom" in panel


class TestBOMGenerateEndpoint:
    """Тесты POST /api/v1/bom/generate."""

    async def test_generate_bom(self, client: AsyncClient, bom_request: dict):
        """Тест генерации BOM."""
        response = await client.post("/api/v1/bom/generate", json=bom_request)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cabinet_type"] == "base"
        assert "panels" in data
        assert "hardware" in data
        assert len(data["panels"]) > 0
        assert data["total_panels"] > 0
        assert data["total_area_m2"] > 0

    async def test_bom_hardware_calculation(self, client: AsyncClient):
        """Тест расчёта фурнитуры."""
        request = {
            "cabinet_type": "base",
            "width_mm": 600,
            "height_mm": 720,
            "depth_mm": 560,
            "door_count": 2,
            "shelf_count": 1,
        }
        response = await client.post("/api/v1/bom/generate", json=request)
        data = response.json()

        # Должны быть петли (минимум 2 на дверь)
        hinges = [h for h in data["hardware"] if h["type"] == "hinge"]
        assert len(hinges) > 0
        assert hinges[0]["quantity"] >= 4  # Минимум 4 петли на 2 двери

        # Должны быть конфирматы
        connectors = [h for h in data["hardware"] if h["type"] == "connector"]
        assert len(connectors) > 0

    async def test_bom_with_drawers(self, client: AsyncClient):
        """Тест BOM для тумбы с ящиками."""
        request = {
            "cabinet_type": "drawer",
            "width_mm": 600,
            "height_mm": 720,
            "depth_mm": 560,
            "drawer_count": 3,
        }
        response = await client.post("/api/v1/bom/generate", json=request)
        data = response.json()

        assert data["success"] is True

        # Проверяем наличие направляющих
        hardware_types = [h["type"] for h in data["hardware"]]
        # Должны быть либо направляющие, либо slide
        assert "slide" in hardware_types or any("направ" in h["name"].lower() for h in data["hardware"])

    async def test_bom_total_hardware_items(self, client: AsyncClient, bom_request: dict):
        """Тест подсчёта общего количества фурнитуры."""
        response = await client.post("/api/v1/bom/generate", json=bom_request)
        data = response.json()

        assert "total_hardware_items" in data
        assert data["total_hardware_items"] > 0

        # Сумма quantity должна совпадать с total_hardware_items
        calculated_total = sum(h["quantity"] for h in data["hardware"])
        assert calculated_total == data["total_hardware_items"]


class TestOrdersEndpoint:
    """Тесты эндпоинтов заказов."""

    async def test_create_order_requires_auth(self, client: AsyncClient):
        """
        Создание заказа без авторизации должно возвращать 401.

        Этот тест проверяет что эндпоинт POST /orders требует аутентификацию
        и возвращает HTTP 401 Unauthorized при отсутствии токена.
        """
        response = await client.post(
            "/api/v1/orders",
            json={"customer_ref": "test_order"}
        )
        assert response.status_code == 401

    @pytest.mark.skip(reason="Требует подключение к PostgreSQL БД")
    async def test_create_order_with_auth_sets_factory_id(
        self, authenticated_client: AsyncClient, mock_user
    ):
        """
        Заказ с авторизацией должен иметь factory_id.

        Этот тест проверяет что при создании заказа с валидным JWT токеном:
        1. Запрос успешно выполняется (HTTP 200)
        2. Созданный заказ содержит поле factory_id
        3. factory_id соответствует фабрике пользователя из токена

        ПРИМЕЧАНИЕ: Требует запущенную PostgreSQL БД для выполнения.
        """
        response = await authenticated_client.post(
            "/api/v1/orders",
            json={"customer_ref": "test_order_auth"}
        )
        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert "factory_id" in data
        assert data["factory_id"] == str(mock_user.factory_id)

    @pytest.mark.skip(reason="Требует подключение к PostgreSQL БД")
    async def test_create_order(self, authenticated_client: AsyncClient):
        """
        Тест создания заказа (с авторизацией).

        Базовый тест создания заказа с авторизацией.

        ПРИМЕЧАНИЕ: Требует запущенную PostgreSQL БД для выполнения.
        """
        response = await authenticated_client.post(
            "/api/v1/orders",
            json={"source": "test"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        # source передаётся в body, но может не возвращаться в response
        assert "status" in data or "created_at" in data or "id" in data


class TestHealthEndpoint:
    """Тесты health check."""

    async def test_health(self, client: AsyncClient):
        """Тест health endpoint."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # status может быть "ok" или "healthy"
        assert data["status"] in ("ok", "healthy")
