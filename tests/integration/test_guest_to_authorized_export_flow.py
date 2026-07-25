from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.database import SessionLocal
from api.guest_drafts import COOKIE_NAME
from api.main import app
from api.models import MagicToken, Order, ProductConfig, User
from api.settings import settings


@pytest.fixture(autouse=True, scope="module")
def _ensure_schema() -> None:
    """Гарантирует схему БД: test_bom_manufacturing_persistence дропает все
    таблицы в teardown, поэтому к этому файлу БД может прийти пустой.
    create_all создаёт metadata-схему (эквивалент head) и no-op, если таблицы есть."""
    import os

    from sqlalchemy import create_engine, text

    from api.database import Base

    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://test_user:test_only_password@127.0.0.1:5434/furniture_ai_test",
    ).replace("+asyncpg", "+psycopg")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(conn)
    engine.dispose()


@pytest.mark.asyncio
async def test_guest_to_authorized_export_flow_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force mock mode settings for hermetic testing
    monkeypatch.setattr(settings, "MVP_MACHINE_FEATURES_ENABLED", False)

    async def mock_rate_limit(*args, **kwargs):
        return True, None, None
    monkeypatch.setattr("api.guest_upload.check_guest_rate_limits", mock_rate_limit)

    transport = ASGITransport(app=app)
    
    # 1. Гость запрашивает ручной grant на загрузку
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/orders/anonymous/grant")
        assert resp.status_code == 200
        grant = resp.json()["guest_upload_grant"]
        
        # Получаем куку гостевой сессии для изоляции
        guest_session_cookie = resp.cookies.get("ar_guest_session")
        assert guest_session_cookie is not None

        # 2. Создаем анонимный заказ по этому гранту
        client.headers["X-Guest-Upload-Grant"] = grant
        order_data = {
            "cabinet_type": "wall",
            "width_mm": 600,
            "height_mm": 720,
            "depth_mm": 300,
        }
        resp = await client.post("/api/v1/orders/anonymous", json=order_data)
        assert resp.status_code == 200
        order_id = resp.json()["id"]
        
        # Проверяем, что выставилась кука гостевого черновика ar_guest_draft
        draft_cookie = resp.cookies.get(COOKIE_NAME)
        assert draft_cookie is not None

        # 3. Делаем AI-уточнение по этому заказу (работает с кукой)
        print("CLIENT COOKIES BEFORE CLARIFY:", client.cookies)
        resp = await client.post(
            "/api/v1/dialogue/clarify",
            json={
                "order_id": order_id,
                "messages": [{"role": "user", "content": "сделай ширину 800"}],
                "current_params": {"cabinet_type": "wall", "width_mm": 600, "height_mm": 720, "depth_mm": 300}
            }
        )
        print("CLARIFY RESPONSE STATUS:", resp.status_code)
        print("CLARIFY RESPONSE TEXT:", resp.text)
        assert resp.status_code == 200
        # 4. Генерируем BOM черновика (работает с кукой)
        resp = await client.post(
            "/api/v1/bom/generate",
            json={
                "order_id": order_id,
                "cabinet_type": "wall",
                "width_mm": 800,
                "height_mm": 720,
                "depth_mm": 300,
                "material": "ЛДСП",
                "thickness_mm": 16,
                "shelf_count": 2,
                "door_count": 2,
                "drawer_count": 0,
            }
        )
        assert resp.status_code == 200

        # 5. Запускаем регистрацию пользователя
        reg_email = f"owner_{uuid4().hex[:8]}@avtoraskroy.ru"
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": reg_email, "factory_name": "Plywood Corp"}
        )
        assert resp.status_code == 201
        
        # Получаем magic token из базы
        async with SessionLocal() as session:
            import sqlalchemy as sa
            result = await session.execute(
                sa.select(MagicToken)
                .join(User)
                .where(User.email == reg_email, MagicToken.used == False)
            )
            magic_token = result.scalar_one().token

        # 6. Верифицируем токен и получаем JWT
        resp = await client.post("/api/v1/auth/verify", json={"token": magic_token})
        assert resp.status_code == 200
        jwt_token = resp.json()["access_token"]
        user_id = resp.json()["user"]["id"]
        factory_id = resp.json()["user"]["factory"]["id"]

        # 7. Привязываем гостевой черновик к аккаунту (CLAIM)
        # Отправляем JWT заголовок и передаем куку
        client.headers["Authorization"] = f"Bearer {jwt_token}"
        resp = await client.post("/api/v1/auth/claim-guest-draft")
        assert resp.status_code == 200
        assert resp.json()["claimed"] is True
        assert resp.json()["order_id"] == order_id

        # Проверяем в БД, что заказ и конфиг привязаны к фабрике
        async with SessionLocal() as session:
            db_order = await session.get(Order, uuid4() if isinstance(order_id, str) == False else order_id)
            assert db_order is not None
            assert str(db_order.factory_id) == factory_id
            assert str(db_order.created_by_id) == user_id

            # Проверяем также ProductConfig
            product_res = await session.execute(
                sa.select(ProductConfig).where(ProductConfig.order_id == db_order.id)
            )
            product = product_res.scalar_one_or_none()
            assert product is not None

        # 8. Пробуем получить чертежи и спецификации (для авторизованного владельца)
        # CAM G-code должен возвращать 404 (флаг выключен)
        resp = await client.post(
            "/api/v1/cam/gcode",
            json={"dxf_artifact_id": str(uuid4()), "machine_profile": "weihong"}
        )
        assert resp.status_code == 404
