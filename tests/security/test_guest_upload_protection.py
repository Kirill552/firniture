"""Строгие тесты защиты публичной загрузки."""

from __future__ import annotations

import base64
import io
from collections import defaultdict
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image, ImageDraw
from starlette.requests import Request

from api import guest_upload
from api.main import app


class FakeRedis:
    """Минимальный Redis double с атомарной семантикой Lua для тестируемых операций."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.zsets: dict[str, dict[str, float]] = defaultdict(dict)

    async def set(self, key: str, value: str, *, ex: int | None = None, nx: bool = False) -> bool:
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def delete(self, key: str) -> int:
        existed = key in self.values
        self.values.pop(key, None)
        return int(existed)

    async def eval(self, _script: str, numkeys: int, *args: Any) -> Any:
        keys = [str(value) for value in args[:numkeys]]
        argv = list(args[numkeys:])
        if numkeys == 1:
            expected = str(argv[0])
            if self.values.get(keys[0]) != expected:
                return 0
            del self.values[keys[0]]
            return 1

        burst_key, daily_key = keys
        now = float(argv[0])
        member = str(argv[1])
        burst_window = int(argv[2])
        burst_limit = int(argv[3])
        daily_window = int(argv[4])
        daily_limit = int(argv[5])
        for key, window in ((burst_key, burst_window), (daily_key, daily_window)):
            self.zsets[key] = {
                name: score for name, score in self.zsets[key].items() if score > now - window
            }
        if len(self.zsets[burst_key]) >= burst_limit:
            oldest = min(self.zsets[burst_key].values())
            return [0, max(1, int(burst_window - (now - oldest)))]
        if len(self.zsets[daily_key]) >= daily_limit:
            oldest = min(self.zsets[daily_key].values())
            return [0, max(1, int(daily_window - (now - oldest)))]
        self.zsets[burst_key][member] = now
        self.zsets[daily_key][member] = now
        return [1, 0]


def make_jpeg(*, blank: bool = False) -> bytes:
    image = Image.new("RGB", (640, 480), (245, 245, 240))
    if not blank:
        draw = ImageDraw.Draw(image)
        draw.rectangle((80, 60, 560, 420), outline=(20, 20, 20), width=5)
        draw.line((320, 60, 320, 420), fill=(40, 40, 40), width=3)
        draw.line((80, 240, 560, 240), fill=(40, 40, 40), width=3)
    output = io.BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()


def encoded(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    redis = FakeRedis()

    async def get_redis() -> FakeRedis:
        return redis

    monkeypatch.setattr(guest_upload, "_redis_client", get_redis)
    monkeypatch.setattr(
        guest_upload.settings,
        "GUEST_UPLOAD_SECRET",
        "test-guest-upload-secret-that-is-long-enough-2026",
    )
    return redis


@pytest.mark.asyncio
async def test_redis_outage_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def unavailable() -> None:
        raise ConnectionError("redis down")

    monkeypatch.setattr(guest_upload, "_redis_client", unavailable)
    monkeypatch.setattr(
        guest_upload.settings,
        "GUEST_UPLOAD_SECRET",
        "test-guest-upload-secret-that-is-long-enough-2026",
    )
    identity = guest_upload.GuestIdentity("identity", "127.0.0.1", "session")

    assert await guest_upload.check_guest_rate_limits(identity) == (
        False,
        None,
        "service_unavailable",
    )
    assert await guest_upload.acquire_analysis_lock(identity) is None
    with pytest.raises(ConnectionError):
        await guest_upload.issue_guest_upload_grant(b"verified")
    assert await guest_upload.validate_and_consume_grant("invalid") is False


def test_missing_secret_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guest_upload.settings, "GUEST_UPLOAD_SECRET", "")
    with pytest.raises(RuntimeError, match="GUEST_UPLOAD_SECRET"):
        guest_upload._get_secret()


@pytest.mark.asyncio
async def test_grant_is_single_use(fake_redis: FakeRedis) -> None:
    token = await guest_upload.issue_guest_upload_grant(b"verified-file")
    assert await guest_upload.validate_and_consume_grant(token) is True
    assert await guest_upload.validate_and_consume_grant(token) is False
    assert await guest_upload.validate_and_consume_grant(token + "00") is False


@pytest.mark.asyncio
async def test_rate_limit_counts_every_attempt(fake_redis: FakeRedis) -> None:
    identity = guest_upload.GuestIdentity("identity", "127.0.0.1", "session")
    for _ in range(3):
        assert await guest_upload.check_guest_rate_limits(identity) == (True, None, None)
    allowed, retry_after, reason = await guest_upload.check_guest_rate_limits(identity)
    assert allowed is False
    assert reason == "rate_limited"
    assert retry_after is not None and retry_after > 0


@pytest.mark.asyncio
async def test_clearing_session_cookie_does_not_bypass_ip_limit(fake_redis: FakeRedis) -> None:
    first_session = guest_upload.GuestIdentity("session-a", "127.0.0.1", "a", "same-ip")
    second_session = guest_upload.GuestIdentity("session-b", "127.0.0.1", "b", "same-ip")
    for _ in range(3):
        assert (await guest_upload.check_guest_rate_limits(first_session))[0] is True
    allowed, _, reason = await guest_upload.check_guest_rate_limits(second_session)
    assert allowed is False
    assert reason == "rate_limited"


def test_untrusted_forwarded_for_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guest_upload.settings, "TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-forwarded-for", b"203.0.113.9")],
        "client": ("198.51.100.5", 1234),
        "server": ("test", 80),
        "scheme": "http",
        "query_string": b"",
    }
    assert guest_upload.get_trusted_client_ip(Request(scope)) == "198.51.100.5"


@pytest.mark.asyncio
async def test_route_returns_strict_validation_statuses(fake_redis: FakeRedis) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        malformed = await client.post(
            "/api/v1/spec/extract-from-image",
            json={"image_base64": "not-base64!", "image_mime_type": "image/jpeg"},
        )
        assert malformed.status_code == 422
        assert malformed.json()["detail"]["code"] == "invalid_base64"

        spoofed = await client.post(
            "/api/v1/spec/extract-from-image",
            json={"image_base64": encoded(make_jpeg()), "image_mime_type": "image/png"},
        )
        assert spoofed.status_code == 415
        assert spoofed.json()["detail"]["code"] == "mime_mismatch"

        blank = await client.post(
            "/api/v1/spec/extract-from-image",
            json={"image_base64": encoded(make_jpeg(blank=True)), "image_mime_type": "image/jpeg"},
        )
        assert blank.status_code == 422
        assert blank.json()["detail"]["code"] == "not_furniture_source"


@pytest.mark.asyncio
async def test_route_returns_503_before_vision_when_redis_is_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def unavailable() -> None:
        raise ConnectionError("redis down")

    monkeypatch.setattr(guest_upload, "_redis_client", unavailable)
    monkeypatch.setattr(
        guest_upload.settings,
        "GUEST_UPLOAD_SECRET",
        "test-guest-upload-secret-that-is-long-enough-2026",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/spec/extract-from-image",
            json={"image_base64": encoded(make_jpeg()), "image_mime_type": "image/jpeg"},
        )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "service_unavailable"


@pytest.mark.asyncio
async def test_production_never_falls_back_to_mock_vision(
    fake_redis: FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        response = await client.post(
            "/api/v1/spec/extract-from-image",
            json={"image_base64": encoded(make_jpeg()), "image_mime_type": "image/jpeg"},
        )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "service_unavailable"
