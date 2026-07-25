from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.auth import create_access_token
from api.database import SessionLocal
from api.main import app
from api.models import Factory, User
from api.settings import settings

@pytest.mark.asyncio
async def test_mvp_features_flag_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    # ── Сценарий 1: Флаг выключен (fail closed) ──
    monkeypatch.setattr(settings, "MVP_MACHINE_FEATURES_ENABLED", False)

    # Setup mock user and factory for authenticated calls
    factory_id = uuid4()
    user_id = uuid4()
    
    async with SessionLocal() as session:
        session.add(Factory(id=factory_id, name="MVP Flag Factory"))
        session.add(User(id=user_id, email=f"user_{uuid4().hex[:8]}@example.com", factory_id=factory_id))
        await session.commit()
        
    jwt_token, _ = create_access_token(user_id, factory_id)
    headers = {"Authorization": f"Bearer {jwt_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /features returns machine_features_enabled = false
        resp = await client.get("/api/v1/features")
        assert resp.status_code == 200
        assert resp.json()["machine_features_enabled"] is False

        # 2. G-code, drilling and machine profiles -> 404
        resp = await client.get("/api/v1/cam/machine-profiles")
        assert resp.status_code == 404

        resp = await client.post("/api/v1/cam/gcode", json={"dxf_artifact_id": str(uuid4()), "machine_profile": "weihong"}, headers=headers)
        assert resp.status_code == 404

        resp = await client.post("/api/v1/cam/drilling", json={"order_id": str(uuid4()), "machine_profile": "weihong"}, headers=headers)
        assert resp.status_code == 404

        # 3. PATCH settings with machine_profile -> 422
        resp = await client.patch(
            "/api/v1/settings",
            json={"machine_profile": "syntec"},
            headers=headers
        )
        assert resp.status_code == 422
        assert "Станочные ЧПУ-функции отключены" in resp.json()["detail"]

        # 4. PATCH settings without machine_profile (e.g. only sheet_width_mm) -> NOT 422 because of feature flag
        resp = await client.patch(
            "/api/v1/settings",
            json={"sheet_width_mm": 2800},
            headers=headers
        )
        # It might succeed (200) or fail due to other validation, but it should not be blocked by the feature flag
        assert resp.status_code != 422

    # ── Сценарий 2: Флаг включен ──
    monkeypatch.setattr(settings, "MVP_MACHINE_FEATURES_ENABLED", True)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /features returns machine_features_enabled = true
        resp = await client.get("/api/v1/features")
        assert resp.status_code == 200
        assert resp.json()["machine_features_enabled"] is True

        # 2. G-code, drilling and machine profiles -> NOT 404 (returns list or validation error, but not 404 feature block)
        resp = await client.get("/api/v1/cam/machine-profiles")
        assert resp.status_code == 200

        # 3. PATCH settings with machine_profile -> NOT 422 (returns 200/success or other validation, but not feature block 422)
        resp = await client.patch(
            "/api/v1/settings",
            json={"machine_profile": "syntec"},
            headers=headers
        )
        assert resp.status_code == 200
