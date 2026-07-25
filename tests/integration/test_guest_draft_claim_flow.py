from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.auth import create_access_token
from api.database import SessionLocal
from api.guest_drafts import COOKIE_NAME, create_guest_draft_token
from api.main import app
from api.models import Factory, Order, User
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
async def test_guest_draft_isolation_and_claim_flow() -> None:
    # 1. Создаем тестовых пользователей и фабрики в БД для проверки авторизованного доступа и claim
    factory_a_id = uuid4()
    factory_b_id = uuid4()
    user_a_id = uuid4()
    user_b_id = uuid4()
    user_a_email = f"user_a_{uuid4().hex[:8]}@example.com"
    user_b_email = f"user_b_{uuid4().hex[:8]}@example.com"
    
    order_a_id = uuid4()
    order_b_id = uuid4()
    
    async with SessionLocal() as session:
        # Фабрики
        session.add(Factory(id=factory_a_id, name="Factory A"))
        session.add(Factory(id=factory_b_id, name="Factory B"))
        # Пользователи
        session.add(User(id=user_a_id, email=user_a_email, factory_id=factory_a_id))
        session.add(User(id=user_b_id, email=user_b_email, factory_id=factory_b_id))
        # Гостевые заказы (factory_id = None, created_by_id = None)
        session.add(Order(id=order_a_id, notes="Guest Order A", factory_id=None, created_by_id=None))
        session.add(Order(id=order_b_id, notes="Guest Order B", factory_id=None, created_by_id=None))
        
        await session.commit()

    # Токены JWT для пользователей
    jwt_a, _ = create_access_token(user_a_id, factory_a_id)
    jwt_b, _ = create_access_token(user_b_id, factory_b_id)
    
    # 2. Генерируем подписанные ar_guest_draft куки для Guest A и Guest B
    cookie_a = create_guest_draft_token(str(order_a_id), "session_a", settings.GUEST_UPLOAD_SECRET)
    cookie_b = create_guest_draft_token(str(order_b_id), "session_b", settings.GUEST_UPLOAD_SECRET)
    
    transport = ASGITransport(app=app)
    
    # Тест 1: Запрос без cookie к гостевому чертежу A -> 403
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Вызываем clarify
        resp = await client.post(
            "/api/v1/dialogue/clarify",
            json={"order_id": str(order_a_id), "messages": [{"role": "user", "content": "test"}]}
        )
        assert resp.status_code == 403

    # Тест 2: Guest A с cookie_a делает clarify для order_a -> УСПЕХ (200 / StreamingResponse)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(COOKIE_NAME, cookie_a)
        resp = await client.post(
            "/api/v1/dialogue/clarify",
            json={"order_id": str(order_a_id), "messages": [{"role": "user", "content": "test"}]}
        )
        assert resp.status_code == 200

    # Тест 2.1: Guest B с cookie_b делает clarify для order_b -> УСПЕХ (200)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(COOKIE_NAME, cookie_b)
        resp = await client.post(
            "/api/v1/dialogue/clarify",
            json={"order_id": str(order_b_id), "messages": [{"role": "user", "content": "test"}]}
        )
        assert resp.status_code == 200

    # Тест 3: Guest A с cookie_a пытается прочитать order_b -> 403
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(COOKIE_NAME, cookie_a)
        resp = await client.post(
            "/api/v1/dialogue/clarify",
            json={"order_id": str(order_b_id), "messages": [{"role": "user", "content": "test"}]}
        )
        assert resp.status_code == 403

    # Тест 4: Авторизованный User A пытается прочитать unclaimed order_a БЕЗ cookie -> 403
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {jwt_a}"
        resp = await client.post(
            "/api/v1/dialogue/clarify",
            json={"order_id": str(order_a_id), "messages": [{"role": "user", "content": "test"}]}
        )
        assert resp.status_code == 403

    # Тест 5: User A выполняет CLAIM заказа A -> 200 УСПЕХ
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {jwt_a}"
        client.cookies.set(COOKIE_NAME, cookie_a)
        resp = await client.post("/api/v1/auth/claim-guest-draft")
        assert resp.status_code == 200
        data = resp.json()
        assert data["claimed"] is True
        assert data["order_id"] == str(order_a_id)
        
        # Проверяем, что кука удалена в ответе
        set_cookie_headers = resp.headers.get_list("set-cookie")
        assert len(set_cookie_headers) > 0
        assert COOKIE_NAME in set_cookie_headers[0]
        assert "Max-Age=0" in set_cookie_headers[0] or "1970" in set_cookie_headers[0]

    # Проверяем в БД, что заказ привязан к фабрике A и пользователю A
    async with SessionLocal() as session:
        db_order = await session.get(Order, order_a_id)
        assert db_order.factory_id == factory_a_id
        assert db_order.created_by_id == user_a_id

    # Тест 6: Повторный claim от того же пользователя -> 200 (идемпотентность)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {jwt_a}"
        # Генерируем свежую куку для повторного запроса
        client.cookies.set(COOKIE_NAME, cookie_a)
        resp = await client.post("/api/v1/auth/claim-guest-draft")
        assert resp.status_code == 200
        assert resp.json()["claimed"] is True

    # Тест 7: Другой пользователь (User B) пытается привязать заказ A -> 409 CONFLICT
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {jwt_b}"
        client.cookies.set(COOKIE_NAME, cookie_a)
        resp = await client.post("/api/v1/auth/claim-guest-draft")
        assert resp.status_code == 409

    # Тест 8: Доступ к привязанному заказу A для User A без куки -> УСПЕХ (так как теперь это его заказ)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {jwt_a}"
        resp = await client.post(
            "/api/v1/dialogue/clarify",
            json={"order_id": str(order_a_id), "messages": [{"role": "user", "content": "test"}]}
        )
        assert resp.status_code == 200

    # Тест 9: Доступ к привязанному заказу A для User B без куки -> 403 (mismatch фабрики)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {jwt_b}"
        resp = await client.post(
            "/api/v1/dialogue/clarify",
            json={"order_id": str(order_a_id), "messages": [{"role": "user", "content": "test"}]}
        )
        assert resp.status_code == 403
