import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cost_estimate_endpoint(async_client: AsyncClient, created_order):
    order_id = created_order["id"]

    # 1. Create product config (finalize order) to have panels
    product_data = {
        "furniture_type": "напольная тумба",
        "dimensions": {"width_mm": 600, "height_mm": 720, "depth_mm": 560},
        "body_material": {"type": "ЛДСП", "thickness_mm": 16, "color": "белый"},
        "door_count": 2,
        "panels": [
            {"name": "Боковина", "width_mm": 720, "height_mm": 560},
            {"name": "Дно", "width_mm": 600, "height_mm": 560},
        ],
    }

    response = await async_client.post(f"/api/v1/orders/{order_id}/finalize", json=product_data)
    assert response.status_code == 200

    # 2. Get cost estimate
    response = await async_client.get(f"/api/v1/orders/{order_id}/cost")
    assert response.status_code == 200
    data = response.json()

    assert "total_cost" in data
    assert data["total_cost"] > 0
    assert "breakdown" in data
    assert len(data["breakdown"]) > 0

    # Check breakdown items
    items = data["breakdown"]
    assert any("ЛДСП" in item["name"] for item in items)
    assert any("Распил" in item["name"] for item in items)
