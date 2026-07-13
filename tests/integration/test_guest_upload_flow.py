"""Интеграционный guest flow: upload -> grant -> один anonymous order."""

from __future__ import annotations

import base64
import io
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image, ImageDraw

from api import guest_upload, routers
from api.main import app
from api.schemas import Order
from tests.security.test_guest_upload_protection import FakeRedis


def furniture_jpeg() -> str:
    image = Image.new("RGB", (640, 480), (245, 245, 240))
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 60, 560, 420), outline=(20, 20, 20), width=5)
    draw.line((320, 60, 320, 420), fill=(40, 40, 40), width=3)
    output = io.BytesIO()
    image.save(output, format="JPEG")
    return base64.b64encode(output.getvalue()).decode("ascii")


@pytest.mark.asyncio
async def test_valid_upload_grant_creates_exactly_one_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = FakeRedis()

    async def get_redis() -> FakeRedis:
        return redis

    monkeypatch.setattr(guest_upload, "_redis_client", get_redis)
    monkeypatch.setattr(
        guest_upload.settings,
        "GUEST_UPLOAD_SECRET",
        "test-guest-upload-secret-that-is-long-enough-2026",
    )

    async def create_order(**_kwargs: object) -> Order:
        now = datetime.now(UTC)
        return Order(id=uuid4(), notes="Черновик после распознавания", created_at=now, updated_at=now)

    monkeypatch.setattr(routers.crud, "create_order", create_order)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        extraction = await client.post(
            "/api/v1/spec/extract-from-image",
            json={"image_base64": furniture_jpeg(), "image_mime_type": "image/jpeg"},
        )
        assert extraction.status_code == 200
        grant = extraction.json()["guest_upload_grant"]
        assert isinstance(grant, str) and grant

        created = await client.post(
            "/api/v1/orders/anonymous",
            headers={"X-Guest-Upload-Grant": grant},
            json={"notes": "Черновик после распознавания"},
        )
        assert created.status_code == 200

        reused = await client.post(
            "/api/v1/orders/anonymous",
            headers={"X-Guest-Upload-Grant": grant},
            json={"notes": "Повтор"},
        )
        assert reused.status_code == 409


@pytest.mark.asyncio
async def test_anonymous_order_without_grant_is_rejected() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/orders/anonymous",
            json={"notes": "Прямой спам"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rate_limited_manual_flow_can_get_one_time_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = FakeRedis()

    async def get_redis() -> FakeRedis:
        return redis

    async def create_order(**_kwargs: object) -> Order:
        now = datetime.now(UTC)
        return Order(id=uuid4(), notes="Ручной черновик", created_at=now, updated_at=now)

    monkeypatch.setattr(guest_upload, "_redis_client", get_redis)
    monkeypatch.setattr(
        guest_upload.settings,
        "GUEST_UPLOAD_SECRET",
        "test-guest-upload-secret-that-is-long-enough-2026",
    )
    monkeypatch.setattr(routers.crud, "create_order", create_order)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        grant_response = await client.post("/api/v1/orders/anonymous/grant")
        assert grant_response.status_code == 200
        grant = grant_response.json()["guest_upload_grant"]
        created = await client.post(
            "/api/v1/orders/anonymous",
            headers={"X-Guest-Upload-Grant": grant},
            json={"notes": "Ручной черновик"},
        )
    assert created.status_code == 200
